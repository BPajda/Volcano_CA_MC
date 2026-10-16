?sweep@PottsMC@volcano@@QEAA_KXZ PROC			; volcano::PottsMC::sweep, COMDAT

; 194  : std::uint64_t PottsMC::sweep() {

$LN127:
	push	rbx
	push	rsi
	push	r12
	sub	rsp, 192				; 000000c0H

; 197  :     const std::uint64_t otherStates = static_cast<std::uint64_t>(p_.Q - 1);

	mov	eax, DWORD PTR [rcx+24]

; 199  :     std::uint64_t acceptedNow = 0;

	xor	esi, esi
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1877 :         return static_cast<size_type>(_My_data._Mylast - _My_data._Myfirst);

	mov	r8, QWORD PTR [rcx+208]
; File <repo>\engine\src\mc\PottsMC.cpp

; 197  :     const std::uint64_t otherStates = static_cast<std::uint64_t>(p_.Q - 1);

	dec	eax
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1877 :         return static_cast<size_type>(_My_data._Mylast - _My_data._Myfirst);

	sub	r8, QWORD PTR [rcx+200]
; File <repo>\engine\src\mc\PottsMC.cpp

; 195  :     const std::uint64_t t = static_cast<std::uint64_t>(sweeps_);

	xor	r12d, r12d
	movsxd	r10, DWORD PTR [rcx+248]
	mov	rbx, rcx
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1872 :         return _My_data._Myfirst == _My_data._Mylast;

	mov	r9, QWORD PTR [rcx+152]
	mov	r11, QWORD PTR [rcx+160]

; 1877 :         return static_cast<size_type>(_My_data._Mylast - _My_data._Myfirst);

	sar	r8, 3
; File <repo>\engine\src\mc\PottsMC.cpp

; 197  :     const std::uint64_t otherStates = static_cast<std::uint64_t>(p_.Q - 1);

	cdqe
	mov	QWORD PTR t$1$[rsp], r10
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1877 :         return static_cast<size_type>(_My_data._Mylast - _My_data._Myfirst);

	mov	QWORD PTR n$1$[rsp], r8
; File <repo>\engine\src\mc\PottsMC.cpp

; 197  :     const std::uint64_t otherStates = static_cast<std::uint64_t>(p_.Q - 1);

	mov	QWORD PTR otherStates$1$[rsp], rax
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1872 :         return _My_data._Myfirst == _My_data._Mylast;

	mov	QWORD PTR tv998[rsp], r9
	mov	QWORD PTR tv997[rsp], r11
; File <repo>\engine\src\mc\PottsMC.cpp

; 199  :     std::uint64_t acceptedNow = 0;

	mov	QWORD PTR acceptedNow$1$[rsp], rsi

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	test	r8, r8
	je	$LN3@sweep
	mov	QWORD PTR [rsp+184], rbp
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	mov	rcx, -6884282663029611473		; a0761d6478bd642fH
; File <repo>\engine\src\mc\PottsMC.cpp

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	mov	QWORD PTR [rsp+176], rdi
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	mov	rdi, 7046029254386353131		; 61c8864680b583ebH
; File <repo>\engine\src\mc\PottsMC.cpp

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	mov	QWORD PTR [rsp+168], r13
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	mov	r13, -7723592293110705685		; 94d049bb133111ebH
; File <repo>\engine\src\mc\PottsMC.cpp

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	mov	QWORD PTR [rsp+160], r14
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	mov	r14, -4658895280553007687		; bf58476d1ce4e5b9H
; File <repo>\engine\src\mc\PottsMC.cpp

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	mov	QWORD PTR [rsp+152], r15
	movaps	XMMWORD PTR [rsp+80], xmm9
	xorps	xmm9, xmm9
	movaps	XMMWORD PTR [rsp+64], xmm10
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	movsd	xmm10, QWORD PTR __real@3ca0000000000000
; File <repo>\engine\src\mc\PottsMC.cpp

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	movaps	XMMWORD PTR [rsp+48], xmm11
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	movsd	xmm11, QWORD PTR __xmm@80000000000000008000000000000000
	movaps	XMMWORD PTR [rsp+128], xmm6
	movaps	XMMWORD PTR [rsp+112], xmm7
	movaps	XMMWORD PTR [rsp+96], xmm8
$LL4@sweep:
; File <repo>\engine\src\core\Rng.hpp

; 48   :     std::uint64_t h = splitmix64(seed ^ 0xA0761D6478BD642FULL);

	mov	r15, QWORD PTR [rbx+16]
	mov	rax, r15
	xor	rax, rcx

; 36   :     x += 0x9E3779B97F4A7C15ULL;

	sub	rax, rdi

; 37   :     x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;

	mov	rcx, rax
	shr	rcx, 30
	xor	rcx, rax
	imul	rcx, r14

; 38   :     x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;

	mov	rax, rcx
	shr	rax, 27
	xor	rax, rcx
	imul	rax, r13

; 39   :     return x ^ (x >> 31);

	mov	rcx, rax
	shr	rcx, 31

; 49   :     h = splitmix64(h ^ step);

	xor	rcx, rax
	xor	rcx, r10

; 36   :     x += 0x9E3779B97F4A7C15ULL;

	sub	rcx, rdi

; 37   :     x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;

	mov	rax, rcx
	shr	rax, 30
	xor	rax, rcx
	imul	rax, r14

; 38   :     x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;

	mov	rcx, rax
	shr	rcx, 27
	xor	rcx, rax
	imul	rcx, r13

; 39   :     return x ^ (x >> 31);

	mov	rdx, rcx
	shr	rdx, 31

; 50   :     h = splitmix64(h ^ globalIndex);

	xor	rdx, rcx
	xor	rdx, r12

; 36   :     x += 0x9E3779B97F4A7C15ULL;

	sub	rdx, rdi

; 37   :     x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;

	mov	rax, rdx
	shr	rax, 30
	xor	rax, rdx
	imul	rax, r14

; 38   :     x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;

	mov	rcx, rax
	shr	rcx, 27
	xor	rcx, rax
	imul	rcx, r13

; 39   :     return x ^ (x >> 31);

	mov	rbp, rcx
	shr	rbp, 31

; 51   :     return splitmix64(h ^ salt);

	xor	rbp, rcx
	mov	rcx, 5567381839951905605		; 4d435049434b4345H
	mov	rax, rbp
	xor	rax, rcx

; 36   :     x += 0x9E3779B97F4A7C15ULL;

	sub	rax, rdi

; 37   :     x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;

	mov	rcx, rax
	shr	rcx, 30
	xor	rcx, rax
	imul	rcx, r14

; 38   :     x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;

	mov	rdx, rcx
	shr	rdx, 27
	xor	rdx, rcx
	imul	rdx, r13

; 39   :     return x ^ (x >> 31);

	mov	rax, rdx
	shr	rax, 31
	xor	rax, rdx
; File <repo>\engine\src\mc\PottsMC.cpp

; 205  :         const std::size_t k = static_cast<std::size_t>(hashRand(p_.seed, t, a, kSaltMcPick) % n);

	xor	edx, edx
	div	r8

; 206  :         const std::size_t i = domainFrame_[k];

	mov	rax, QWORD PTR [rbx+200]
	mov	r13, rdx
	mov	rdi, QWORD PTR [rax+rdx*8]
	lea	r14, QWORD PTR [rdi*4]

; 210  :         if (useMobility && hashUniform(p_.seed, t, a, kSaltMcMobility) >= static_cast<double>(mobility_[i])) {

	cmp	r9, r11
	je	SHORT $LN100@sweep
; File <repo>\engine\src\core\Rng.hpp

; 57   :     return static_cast<double>(hashRand(seed, step, globalIndex, salt) >> 11) *

	mov	r9, 5567378567169920073			; 4d434d4f42494c49H
	mov	r8, r12
	mov	rdx, r10
	mov	rcx, r15
	call	?hashRand@volcano@@YA_K_K000@Z		; volcano::hashRand
	mov	rcx, rax
	xorps	xmm1, xmm1
	shr	rcx, 11
	test	rcx, rcx
	js	SHORT $LN105@sweep
	cvtsi2sd xmm1, rcx
	jmp	SHORT $LN106@sweep
$LN105@sweep:
	mov	rax, rcx
	and	ecx, 1
	shr	rax, 1
	or	rax, rcx
	cvtsi2sd xmm1, rax
	addsd	xmm1, xmm1
$LN106@sweep:
; File <repo>\engine\src\mc\PottsMC.cpp

; 210  :         if (useMobility && hashUniform(p_.seed, t, a, kSaltMcMobility) >= static_cast<double>(mobility_[i])) {

	mov	rax, QWORD PTR [rbx+152]
; File <repo>\engine\src\core\Rng.hpp

; 57   :     return static_cast<double>(hashRand(seed, step, globalIndex, salt) >> 11) *

	mulsd	xmm1, xmm10
	movss	xmm0, DWORD PTR [r14+rax]
; File <repo>\engine\src\mc\PottsMC.cpp

; 210  :         if (useMobility && hashUniform(p_.seed, t, a, kSaltMcMobility) >= static_cast<double>(mobility_[i])) {

	cvtps2pd xmm0, xmm0
	comisd	xmm1, xmm0
	jae	$LN109@sweep
	mov	r10, QWORD PTR t$1$[rsp]
$LN100@sweep:

; 211  :             continue;
; 212  :         }
; 213  :         ++attempts_;

	inc	QWORD PTR [rbx+256]
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1877 :         return static_cast<size_type>(_My_data._Mylast - _My_data._Myfirst);

	mov	rsi, QWORD PTR [rbx+64]
	sub	rsi, QWORD PTR [rbx+56]
; File <repo>\engine\src\core\Neighborhood.hpp

; 43   :         if (variants_.size() == 1) {

	lea	rax, QWORD PTR [rsi-24]
	cmp	rax, 24
	jae	SHORT $LN28@sweep

; 44   :             return 0;

	xor	edx, edx
	jmp	SHORT $LN27@sweep
$LN28@sweep:

; 45   :         }
; 46   :         const std::uint64_t r = hashRand(seed, step, cellIndex, kSaltNeighborhood);

	mov	r8, QWORD PTR [rbx+224]
	mov	r9, 5639994678855225170			; 4e45494748424f52H
	mov	rdx, r10
	mov	rcx, r15
	mov	r8, QWORD PTR [r8+r13*8]
	call	?hashRand@volcano@@YA_K_K000@Z		; volcano::hashRand
	mov	r8, rax
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1877 :         return static_cast<size_type>(_My_data._Mylast - _My_data._Myfirst);

	mov	rax, 3074457345618258603		; 2aaaaaaaaaaaaaabH
	imul	rsi
	mov	rcx, rdx
; File <repo>\engine\src\core\Neighborhood.hpp

; 47   :         return static_cast<int>(r % variants_.size());

	xor	edx, edx
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1877 :         return static_cast<size_type>(_My_data._Mylast - _My_data._Myfirst);

	sar	rcx, 2
	mov	rax, rcx
	shr	rax, 63					; 0000003fH
	add	rcx, rax
; File <repo>\engine\src\core\Neighborhood.hpp

; 47   :         return static_cast<int>(r % variants_.size());

	mov	rax, r8
	div	rcx
$LN27@sweep:
; File <repo>\engine\src\mc\PottsMC.cpp

; 215  :         const std::int32_t current = spin_[i];

	mov	rax, QWORD PTR [rbx+104]
; File <repo>\engine\src\mc\PottsMC.hpp

; 123  :         int n = 0;

	xor	r9d, r9d
; File <repo>\engine\src\mc\PottsMC.cpp

; 215  :         const std::int32_t current = spin_[i];

	mov	r11d, DWORD PTR [r14+rax]
; File <repo>\engine\src\mc\PottsMC.hpp

; 116  :         return linear_[static_cast<std::size_t>(nb_.variantFor(p_.seed, t, gidx))];

	movsxd	rax, edx
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	lea	rcx, QWORD PTR [rax+rax*2]
	mov	rax, QWORD PTR [rbx+176]
; File <repo>\engine\src\mc\PottsMC.hpp

; 124  :         for (const std::ptrdiff_t o : offsets) {

	mov	r8, QWORD PTR [rax+rcx*8]
	mov	r10, QWORD PTR [rax+rcx*8+8]
	mov	rcx, r8
	cmp	r8, r10
	je	SHORT $LN40@sweep
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	mov	rsi, QWORD PTR [rbx+128]
	npad	11
$LL41@sweep:
; File <repo>\engine\src\mc\PottsMC.hpp

; 125  :             const std::size_t j = static_cast<std::size_t>(static_cast<std::ptrdiff_t>(i) + o);

	mov	rdx, QWORD PTR [rcx]
	add	rdx, rdi

; 126  :             n += ((mask_[j] & kInDomain) != 0 && spin_[j] != s) ? 1 : 0;

	test	BYTE PTR [rsi+rdx], 1
	je	SHORT $LN101@sweep
	mov	rax, QWORD PTR [rbx+104]
	cmp	DWORD PTR [rax+rdx*4], r11d
	je	SHORT $LN101@sweep
	mov	eax, 1
	jmp	SHORT $LN44@sweep
$LN101@sweep:
	xor	eax, eax
$LN44@sweep:
	add	r9d, eax
	add	rcx, 8
	cmp	rcx, r10
	jne	SHORT $LL41@sweep
$LN40@sweep:
; File <repo>\engine\src\mc\PottsMC.cpp

; 224  :         std::int32_t proposed =

	xor	edx, edx
	movd	xmm0, r9d
; File <repo>\engine\src\core\Rng.hpp

; 51   :     return splitmix64(h ^ salt);

	mov	rax, 5567380779195256404		; 4d434f5249454e54H

; 37   :     x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;

	mov	r14, -4658895280553007687		; bf58476d1ce4e5b9H

; 51   :     return splitmix64(h ^ salt);

	xor	rbp, rax

; 38   :     x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;

	mov	r13, -7723592293110705685		; 94d049bb133111ebH
	mov	rax, 7046029254386353131		; 61c8864680b583ebH
	sub	rbp, rax
	mov	rax, rbp
	shr	rax, 30
	xor	rax, rbp
	imul	rax, r14
; File <repo>\engine\src\mc\PottsMC.cpp

; 219  :         const double energyBefore = p_.J * unlikeNeighbors(i, current, offsets);

	cvtdq2pd xmm0, xmm0
; File <repo>\engine\src\core\Rng.hpp

; 38   :     x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;

	mov	rcx, rax
	shr	rcx, 27
; File <repo>\engine\src\mc\PottsMC.cpp

; 219  :         const double energyBefore = p_.J * unlikeNeighbors(i, current, offsets);

	mulsd	xmm0, QWORD PTR [rbx+32]
; File <repo>\engine\src\core\Rng.hpp

; 38   :     x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;

	xor	rcx, rax
	imul	rcx, r13

; 39   :     return x ^ (x >> 31);

	mov	rax, rcx
	shr	rax, 31
	xor	rax, rcx
; File <repo>\engine\src\mc\PottsMC.hpp

; 123  :         int n = 0;

	xor	ecx, ecx
; File <repo>\engine\src\mc\PottsMC.cpp

; 224  :         std::int32_t proposed =

	div	QWORD PTR otherStates$1$[rsp]
	lea	eax, DWORD PTR [rdx+1]
; File <repo>\engine\src\mc\PottsMC.hpp

; 123  :         int n = 0;

	cmp	eax, r11d
	setge	cl
	lea	esi, DWORD PTR [rcx+1]
	add	esi, edx
	xor	edx, edx

; 124  :         for (const std::ptrdiff_t o : offsets) {

	cmp	r8, r10
	je	SHORT $LN61@sweep
; File C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\include\vector

; 1907 :         return _My_data._Myfirst[_Pos];

	mov	r9, QWORD PTR [rbx+128]
	npad	11
$LL62@sweep:
; File <repo>\engine\src\mc\PottsMC.hpp

; 125  :             const std::size_t j = static_cast<std::size_t>(static_cast<std::ptrdiff_t>(i) + o);

	mov	rcx, QWORD PTR [r8]
	add	rcx, rdi

; 126  :             n += ((mask_[j] & kInDomain) != 0 && spin_[j] != s) ? 1 : 0;

	test	BYTE PTR [r9+rcx], 1
	je	SHORT $LN102@sweep
	mov	rax, QWORD PTR [rbx+104]
	cmp	DWORD PTR [rax+rcx*4], esi
	je	SHORT $LN102@sweep
	mov	eax, 1
	jmp	SHORT $LN65@sweep
$LN102@sweep:
	xor	eax, eax
$LN65@sweep:
	add	edx, eax
	add	r8, 8
	cmp	r8, r10
	jne	SHORT $LL62@sweep
$LN61@sweep:
	movd	xmm6, edx
; File <repo>\engine\src\mc\PottsMC.cpp

; 231  :         const double energyAfter = p_.J * unlikeNeighbors(i, proposed, offsets);

	cvtdq2pd xmm6, xmm6
	mulsd	xmm6, QWORD PTR [rbx+32]

; 232  :         const double deltaE = energyAfter - energyBefore;

	subsd	xmm6, xmm0

; 233  : 
; 234  :         // Krok 5: akceptacja Metropolisa — ΔE <= 0 zawsze; ΔE > 0 z prawdopodobieństwem
; 235  :         // exp(−ΔE/kT) (kT > 0), a dla kT = 0 nigdy (p = 0, dokładnie jak w wariancie naiwnym).
; 236  :         // OPTYMALIZACJA: tablica exp(−ΔE/kT) dla możliwych ΔE = J · k.
; 237  :         bool accept = deltaE <= 0.0;

	comisd	xmm9, xmm6
	setae	al

; 238  :         if (!accept && p_.kT > 0.0) {

	test	al, al
	jne	$LN99@sweep
	movsd	xmm8, QWORD PTR [rbx+40]
	comisd	xmm8, xmm9
	jbe	$LN107@sweep
; File <repo>\engine\src\core\Rng.hpp

; 57   :     return static_cast<double>(hashRand(seed, step, globalIndex, salt) >> 11) *

	mov	rdx, QWORD PTR t$1$[rsp]
	mov	r9, 5567365321507295316			; 4d43414343455054H
	mov	r8, r12
	mov	rcx, r15
	call	?hashRand@volcano@@YA_K_K000@Z		; volcano::hashRand
	mov	rcx, rax
	xorps	xmm7, xmm7
	shr	rcx, 11
	test	rcx, rcx
	js	SHORT $LN103@sweep
	cvtsi2sd xmm7, rcx
	jmp	SHORT $LN104@sweep
$LN103@sweep:
	mov	rax, rcx
	and	ecx, 1
	shr	rax, 1
	or	rax, rcx
	cvtsi2sd xmm7, rax
	addsd	xmm7, xmm7
$LN104@sweep:
; File <repo>\engine\src\mc\PottsMC.cpp

; 239  :             accept = hashUniform(p_.seed, t, a, kSaltMcAccept) < std::exp(-deltaE / p_.kT);

	xorps	xmm6, xmm11
; File <repo>\engine\src\core\Rng.hpp

; 57   :     return static_cast<double>(hashRand(seed, step, globalIndex, salt) >> 11) *

	mulsd	xmm7, xmm10
; File <repo>\engine\src\mc\PottsMC.cpp

; 239  :             accept = hashUniform(p_.seed, t, a, kSaltMcAccept) < std::exp(-deltaE / p_.kT);

	divsd	xmm6, xmm8
	movaps	xmm0, xmm6
	call	exp
	comisd	xmm0, xmm7
	seta	cl

; 240  :             uphill_ += accept ? 1 : 0;

	movzx	eax, cl
	add	QWORD PTR [rbx+272], rax

; 241  :         }
; 242  :         if (accept) {

	test	cl, cl
	je	SHORT $LN107@sweep
$LN99@sweep:

; 243  :             spin_[i] = proposed;

	mov	rax, QWORD PTR [rbx+104]
	mov	DWORD PTR [rax+rdi*4], esi

; 244  :             ++acceptedNow;

	mov	rsi, QWORD PTR acceptedNow$1$[rsp]

; 245  :             if ((mask_[i] & kPeriodicEdge) != 0) {

	mov	rax, QWORD PTR [rbx+128]
	inc	rsi
	mov	QWORD PTR acceptedNow$1$[rsp], rsi
	test	BYTE PTR [rdi+rax], 2
	je	SHORT $LN2@sweep

; 246  :                 syncFrame(i);  // kopie komórki w ramce periodycznej muszą zobaczyć zmianę

	mov	rdx, rdi
	mov	rcx, rbx
	call	?syncFrame@PottsMC@volcano@@AEAAX_K@Z	; volcano::PottsMC::syncFrame
	jmp	SHORT $LN2@sweep
$LN107@sweep:

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	mov	rsi, QWORD PTR acceptedNow$1$[rsp]
	jmp	SHORT $LN2@sweep
$LN109@sweep:

; 210  :         if (useMobility && hashUniform(p_.seed, t, a, kSaltMcMobility) >= static_cast<double>(mobility_[i])) {

	mov	r14, -4658895280553007687		; bf58476d1ce4e5b9H
	mov	r13, -7723592293110705685		; 94d049bb133111ebH
$LN2@sweep:

; 202  :     for (std::uint64_t a = 0; a < n; ++a) {

	mov	r8, QWORD PTR n$1$[rsp]
	inc	r12
	mov	r10, QWORD PTR t$1$[rsp]
	mov	rdi, 7046029254386353131		; 61c8864680b583ebH
	mov	r9, QWORD PTR tv998[rsp]
	mov	rcx, -6884282663029611473		; a0761d6478bd642fH
	mov	r11, QWORD PTR tv997[rsp]
	cmp	r12, r8
	jb	$LL4@sweep
	movaps	xmm11, XMMWORD PTR [rsp+48]
	movaps	xmm10, XMMWORD PTR [rsp+64]
	movaps	xmm9, XMMWORD PTR [rsp+80]
	movaps	xmm8, XMMWORD PTR [rsp+96]
	movaps	xmm7, XMMWORD PTR [rsp+112]
	movaps	xmm6, XMMWORD PTR [rsp+128]
	mov	r15, QWORD PTR [rsp+152]
	mov	r14, QWORD PTR [rsp+160]
	mov	r13, QWORD PTR [rsp+168]
	mov	rdi, QWORD PTR [rsp+176]
	mov	rbp, QWORD PTR [rsp+184]
$LN3@sweep:

; 247  :             }
; 248  :         }
; 249  :     }
; 250  :     accepted_ += acceptedNow;

	add	QWORD PTR [rbx+264], rsi

; 251  :     ++sweeps_;
; 252  :     return acceptedNow;

	mov	rax, rsi
	inc	DWORD PTR [rbx+248]

; 253  : }

	add	rsp, 192				; 000000c0H
	pop	r12
	pop	rsi
	pop	rbx
	ret	0
?sweep@PottsMC@volcano@@QEAA_KXZ ENDP			; volcano::PottsMC::sweep
