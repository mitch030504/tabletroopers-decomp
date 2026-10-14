#pragma once
#include <cstdint>
#include <cmath>

// Native ABI candidates derived from the active build. Runtime contracts remain open.
struct ArrayHeader { void* klass; void* monitor; void* bounds; std::uintptr_t length; };
template <class T> struct Array { ArrayHeader header; T data[1]; };
struct Vec3 { float x, y, z; };
struct WaterHandler { char prefix[0xa8]; void* visual; char rest[0x28]; float min_height; float max_height; };
extern "C" {
[[noreturn]] void raise_null();
[[noreturn]] void raise_bounds();
float NetworkRunner_get_DeltaTime(void* runner, void* method_info);
float Time_get_time(void* method_info);
void* GameObject_get_transform(void* visual, void* method_info);
Vec3 Transform_get_localPosition(void* transform, void* method_info);
void Transform_set_localPosition(void* transform, Vec3 value, void* method_info);
}
