#include "core/ChildProcess.hpp"

#include <cstdio>

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  ifndef NOMINMAX
#    define NOMINMAX
#  endif
#  include <windows.h>
#else
#  include <fcntl.h>
#  include <spawn.h>
#  include <sys/wait.h>
#  include <unistd.h>

#  include <cerrno>
#  include <cstring>

extern char** environ;  // środowisko bieżącego procesu — przekazywane programowi potomnemu
#endif

namespace volcano {

namespace fs = std::filesystem;

#ifdef _WIN32

namespace {

// Tekst w stronie kodowej cp (argv z main ma stronę kodową systemu, CP_ACP) -> UTF-16.
std::wstring widen(const std::string& s, UINT cp) {
    if (s.empty()) {
        return {};
    }
    const int n = MultiByteToWideChar(cp, 0, s.data(), static_cast<int>(s.size()), nullptr, 0);
    std::wstring w(static_cast<std::size_t>(n), L'\0');
    MultiByteToWideChar(cp, 0, s.data(), static_cast<int>(s.size()), w.data(), n);
    return w;
}

}  // namespace

std::wstring ChildProcess::quoteArg(const std::wstring& arg) {
    if (!arg.empty() && arg.find_first_of(L" \t\n\v\"") == std::wstring::npos) {
        return arg;
    }
    // Reguły CRT: n ukośników przed cudzysłowem -> 2n + 1 (ukośniki + \"), na końcu argumentu -> 2n
    // (bo zaraz po nich jest zamykający cudzysłów), w pozostałych miejscach ukośniki bez zmian.
    std::wstring out = L"\"";
    for (auto it = arg.begin();; ++it) {
        std::size_t backslashes = 0;
        while (it != arg.end() && *it == L'\\') {
            ++it;
            ++backslashes;
        }
        if (it == arg.end()) {
            out.append(backslashes * 2, L'\\');
            break;
        }
        if (*it == L'"') {
            out.append(backslashes * 2 + 1, L'\\');
        } else {
            out.append(backslashes, L'\\');
        }
        out.push_back(*it);
    }
    out.push_back(L'"');
    return out;
}

fs::path ChildProcess::selfPath() {
    std::wstring buf(MAX_PATH, L'\0');
    for (;;) {
        const DWORD n = GetModuleFileNameW(nullptr, buf.data(), static_cast<DWORD>(buf.size()));
        if (n == 0) {
            return {};
        }
        if (n < buf.size()) {
            buf.resize(n);
            return fs::path(buf);
        }
        buf.resize(buf.size() * 2);  // ścieżka dłuższa niż bufor — powiększamy
    }
}

ChildResult ChildProcess::run(const fs::path& exe, const std::vector<ChildArg>& args, const fs::path& log) {
    ChildResult r;
    std::wstring cmd = quoteArg(exe.wstring());
    for (const ChildArg& a : args) {
        cmd += L' ';
        cmd += quoteArg(a.isPath ? a.path.wstring() : widen(a.text, CP_ACP));
    }

    // Log dziedziczony przez proces potomny jako stdout i stderr; FILE_APPEND_DATA — każdy zapis
    // trafia na koniec pliku, więc oba strumienie się nie nadpisują.
    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.bInheritHandle = TRUE;
    HANDLE logHandle = CreateFileW(log.wstring().c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa,
                                   OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (logHandle == INVALID_HANDLE_VALUE) {
        r.error = "nie można otworzyć pliku logu " + log.u8string() + " (kod " + std::to_string(GetLastError()) + ")";
        return r;
    }

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdInput = nullptr;  // silnik nie czyta ze standardowego wejścia
    si.hStdOutput = logHandle;
    si.hStdError = logHandle;
    PROCESS_INFORMATION pi{};
    std::vector<wchar_t> line(cmd.begin(), cmd.end());
    line.push_back(L'\0');  // CreateProcessW może modyfikować bufor wiersza poleceń
    const BOOL ok = CreateProcessW(exe.wstring().c_str(), line.data(), nullptr, nullptr, TRUE, 0, nullptr, nullptr,
                                   &si, &pi);
    const DWORD startError = ok ? 0 : GetLastError();
    CloseHandle(logHandle);  // proces potomny ma własną kopię uchwytu
    if (!ok) {
        r.error = "nie można uruchomić " + exe.u8string() + " (kod systemu " + std::to_string(startError) + ")";
        return r;
    }
    r.started = true;
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    r.exitCode = static_cast<int>(code);
    if (code >= 0xC0000000UL) {
        // Kody NTSTATUS (np. 0xC0000005 — naruszenie dostępu, 0xC0000017 — brak pamięci).
        char buf[64];
        std::snprintf(buf, sizeof(buf), "proces przerwany wyjątkiem systemu 0x%08lX", static_cast<unsigned long>(code));
        r.error = buf;
    }
    return r;
}

#else  // Linux / inne systemy POSIX

fs::path ChildProcess::selfPath() {
    std::error_code ec;
    const fs::path p = fs::read_symlink("/proc/self/exe", ec);
    return ec ? fs::path() : p;
}

ChildResult ChildProcess::run(const fs::path& exe, const std::vector<ChildArg>& args, const fs::path& log) {
    ChildResult r;
    std::vector<std::string> storage;
    storage.push_back(exe.string());
    for (const ChildArg& a : args) {
        storage.push_back(a.isPath ? a.path.string() : a.text);
    }
    std::vector<char*> argv;
    for (std::string& s : storage) {
        argv.push_back(s.data());
    }
    argv.push_back(nullptr);

    // stdout (1) -> koniec logu, stderr (2) -> to samo co stdout.
    posix_spawn_file_actions_t actions;
    posix_spawn_file_actions_init(&actions);
    posix_spawn_file_actions_addopen(&actions, 1, log.c_str(), O_WRONLY | O_CREAT | O_APPEND, 0644);
    posix_spawn_file_actions_adddup2(&actions, 1, 2);
    pid_t pid = 0;
    const int rc = posix_spawn(&pid, exe.c_str(), &actions, nullptr, argv.data(), environ);
    posix_spawn_file_actions_destroy(&actions);
    if (rc != 0) {
        r.error = "nie można uruchomić " + exe.string() + ": " + std::strerror(rc);
        return r;
    }
    r.started = true;
    int status = 0;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) {
            r.error = std::string("waitpid: ") + std::strerror(errno);
            return r;
        }
    }
    if (WIFEXITED(status)) {
        r.exitCode = WEXITSTATUS(status);
    } else if (WIFSIGNALED(status)) {
        r.exitCode = 128 + WTERMSIG(status);
        r.error = "proces zakończony sygnałem " + std::to_string(WTERMSIG(status));
    }
    return r;
}

#endif

}  // namespace volcano
