#include "game.hpp"

// Only caller arithmetic/ABI is reconstructed; engine and null-helper effects are open.
extern "C" float TicksToSecondsFloat(std::int32_t ticks, void* runner, void* method_info) {
    if (!runner) raise_null();
    return NetworkRunner_get_DeltaTime(runner, nullptr) * static_cast<float>(ticks);
}
