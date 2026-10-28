#include "CloudPayload.h"
#include <cassert>
#include <cstring>
#include <cstdio>

int main() {
    const char* a = "6ae1349f00df8f00089ecc14";
    const char* b = "6ae1349f00df8f00089ecc16";
    const char* c = "6ae1349f00df8f00089ecc18";
    const CloudMeasurement records[] = {{63.9f, 89.6f, 0, 1793145600},
        {65.3f, 95.7f, 1, 1793145660}, {67.1f, 99.9f, UINT32_MAX, 1793145720}};
    char json[1200];
    const size_t length = formatCloudBatch(json, sizeof(json), records, 3, a, b, c);
    assert(length && length == strlen(json) && json[0] == '[' && json[length-1] == ']');
    char tooSmall[50];
    assert(!formatCloudBatch(tooSmall, sizeof(tooSmall), records, 3, a, b, c));
    assert(!formatCloudBatch(json, sizeof(json), records, 0, a, b, c));
    assert(!formatCloudBatch(json, sizeof(json), records, 4, a, b, c));
    assert(!formatCloudBatch(json, 0, records, 1, a, b, c));
    assert(formatCloudBatch(json, sizeof(json), records, 3, a, b, c));
    std::puts(json);
}
