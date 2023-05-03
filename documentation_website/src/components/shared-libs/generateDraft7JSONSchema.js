"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
function generateJsonSchema(obj) {
    if (Array.isArray(obj)) {
        return {
            type: "array",
            items: obj.map(function (s) { return generateJsonSchema(s); }),
        };
    }
    else if (typeof obj === "object" && obj !== null) {
        var properties = {};
        for (var _i = 0, _a = Object.keys(obj); _i < _a.length; _i++) {
            var key = _a[_i];
            properties[key] = generateJsonSchema(obj[key]);
        }
        return {
            type: "object",
            properties: properties,
        };
    }
    else {
        var typeMap = {
            string: { type: "string" },
            number: { type: "number" },
            boolean: { type: "boolean" },
            undefined: { type: "null" },
        };
        return typeMap[typeof obj];
    }
}
function generateJsonSchemaWithRoot(obj) {
    var schema = generateJsonSchema(obj);
    schema["$schema"] = "http://json-schema.org/draft-07/schema#";
    return schema;
}
exports.default = generateJsonSchemaWithRoot;
