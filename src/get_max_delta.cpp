#include "game.hpp"

// Initial candidate. Build/diff determines matching; this is not accepted original source.
extern "C" float GetMaxDelta(void* self, Array<Array<float>*>* weights, std::int32_t active_index, void* method_info) {
    if (!weights) raise_null();
    float result = 0.0f;
    for (std::int32_t i = 0; i < static_cast<std::int32_t>(weights->header.length); ++i) {
        if (static_cast<std::uint32_t>(i) >= weights->header.length) raise_bounds();
        auto row = weights->data[i];
        if (!row) raise_null();
        for (std::int32_t j = 0; j < static_cast<std::int32_t>(row->header.length); ++j) {
            if (static_cast<std::uint32_t>(j) >= row->header.length) raise_bounds();
            float delta = __builtin_fabsf((j == active_index ? 1.0f : 0.0f) - row->data[j]);
            result = result > delta ? result : delta;
        }
    }
    return result;
}
