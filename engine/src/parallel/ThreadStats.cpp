#include "parallel/ThreadStats.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

#include "parallel/Affinity.hpp"

namespace volcano {

namespace {

// Milisekundy zaokrąglone do 0,001 (jak sekcje times.json).
double ms3(double seconds) { return std::round(seconds * 1e6) / 1000.0; }

}  // namespace

ThreadStats::ThreadStats(int threads, std::vector<std::string> phases)
    : threads_(std::max(threads, 1)),
      phases_(std::move(phases)),
      step_(static_cast<std::size_t>(threads_)),
      total_(static_cast<std::size_t>(threads_)),
      phaseMax_(phases_.size(), 0.0),
      phaseMean_(phases_.size(), 0.0),
      cpus_(static_cast<std::size_t>(threads_), 0) {
    if (phases_.size() > static_cast<std::size_t>(kMaxPhases)) {
        phases_.resize(static_cast<std::size_t>(kMaxPhases));
        phaseMax_.resize(phases_.size());
        phaseMean_.resize(phases_.size());
    }
}

void ThreadStats::noteCpu(int tid) {
    const int cpu = CpuAffinity::currentCpu();
    if (cpu >= 0 && cpu < 64) {
        cpus_[static_cast<std::size_t>(tid)] |= std::uint64_t(1) << cpu;
    }
}

void ThreadStats::endStep() {
    const std::size_t nph = phases_.size();
    double mx = 0.0;
    double mn = 0.0;
    double sum = 0.0;
    for (std::size_t ph = 0; ph < nph; ++ph) {
        double pmx = 0.0;
        double psum = 0.0;
        for (std::size_t t = 0; t < step_.size(); ++t) {
            pmx = std::max(pmx, step_[t].v[ph]);
            psum += step_[t].v[ph];
        }
        phaseMax_[ph] += pmx;
        phaseMean_[ph] += psum / static_cast<double>(threads_);
    }
    for (std::size_t t = 0; t < step_.size(); ++t) {
        double work = 0.0;
        for (std::size_t ph = 0; ph < nph; ++ph) {
            work += step_[t].v[ph];
            total_[t].v[ph] += step_[t].v[ph];
            step_[t].v[ph] = 0.0;
        }
        mx = (t == 0) ? work : std::max(mx, work);
        mn = (t == 0) ? work : std::min(mn, work);
        sum += work;
    }
    sumMax_ += mx;
    sumMin_ += mn;
    sumMean_ += sum / static_cast<double>(threads_);
    ++steps_;
}

nlohmann::ordered_json ThreadStats::toJson() const {
    using ojson = nlohmann::ordered_json;
    ojson j;
    j["threads"] = threads_;
    j["steps"] = steps_;
    j["phases"] = phases_;
    // Praca każdego wątku w każdej fazie (suma po krokach).
    ojson work = ojson::object();
    for (std::size_t ph = 0; ph < phases_.size(); ++ph) {
        ojson list = ojson::array();
        for (std::size_t t = 0; t < total_.size(); ++t) {
            list.push_back(ms3(total_[t].v[ph]));
        }
        work[phases_[ph]] = list;
    }
    j["workMs"] = work;
    ojson perThread = ojson::array();
    for (std::size_t t = 0; t < total_.size(); ++t) {
        double s = 0.0;
        for (std::size_t ph = 0; ph < phases_.size(); ++ph) {
            s += total_[t].v[ph];
        }
        perThread.push_back(ms3(s));
    }
    j["threadWorkMs"] = perThread;
    j["stepMaxMs"] = ms3(sumMax_);
    j["stepMeanMs"] = ms3(sumMean_);
    j["stepMinMs"] = ms3(sumMin_);
    j["imbalance"] = sumMean_ > 0.0 ? std::round(sumMax_ / sumMean_ * 1000.0) / 1000.0 : 1.0;
    ojson phaseImb = ojson::object();
    for (std::size_t ph = 0; ph < phases_.size(); ++ph) {
        phaseImb[phases_[ph]] =
            phaseMean_[ph] > 0.0 ? std::round(phaseMax_[ph] / phaseMean_[ph] * 1000.0) / 1000.0 : 1.0;
    }
    j["phaseImbalance"] = phaseImb;
    j["wallMs"] = ms3(wall_);
    // Procesory logiczne, na których pracował każdy wątek.
    ojson cpus = ojson::array();
    for (const std::uint64_t m : cpus_) {
        ojson list = ojson::array();
        for (int c = 0; c < 64; ++c) {
            if ((m >> c) & 1) {
                list.push_back(c);
            }
        }
        cpus.push_back(list);
    }
    j["cpus"] = cpus;
    return j;
}

}  // namespace volcano
