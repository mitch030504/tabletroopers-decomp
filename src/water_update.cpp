#include "game.hpp"

// Bounded finite-value candidate. Exceptional FP and live Unity behavior remain open.
extern "C" void WaterUpdate(WaterHandler* self, void* method_info) {
    float low = self->min_height, high = self->max_height;
    float time = Time_get_time(nullptr);
    if (!self->visual) raise_null();
    void* first = GameObject_get_transform(self->visual, nullptr);
    if (!first) raise_null();
    Vec3 position = Transform_get_localPosition(first, nullptr);
    if (!self->visual) raise_null();
    void* second = GameObject_get_transform(self->visual, nullptr);
    if (!second) raise_null();
    float half = time * 0.5f;
    float phase = half - 2.0f * __builtin_floorf(half * 0.5f);
    phase = phase > 2.0f ? 2.0f : phase;
    phase = phase < 0.0f ? 0.0f : phase;
    float height = 1.0f - __builtin_fabsf(phase - 1.0f);
    height = height > 1.0f ? 1.0f : height;
    height = height < 0.0f ? 0.0f : height;
    position.y = low + (high - low) * height;
    Transform_set_localPosition(second, position, nullptr);
}
