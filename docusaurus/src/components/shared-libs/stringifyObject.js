"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
function stringifyObject(obj, indent) {
    if (indent === void 0) { indent = 2; }
    var keys = Object.keys(obj);
    var pairs = keys.map(function (key) {
        var value = obj[key];
        if (typeof value === "function") {
            var match = value.toString().match(/function\s+([\w$]+)\s*\(([^)]*)\)/);
            var name = match ? match[1] : "anonymous";
            var params = match
                ? match[2]
                    .split(",")
                    .map(function (p) { return p.trim(); })
                    .join(", ")
                : "";
            return "".concat(" ".repeat(indent)).concat(key, ": function ").concat(name, "(").concat(params, ") { /* function body */ },");
        }
        else if (typeof value === "object" &&
            !Array.isArray(value) &&
            value !== null) {
            return "".concat(" ".repeat(indent)).concat(key, ": ").concat(stringifyObject(value, indent + 2), ",");
        }
        else {
            return "".concat(" ".repeat(indent)).concat(key, ": ").concat(JSON.stringify(value), ",");
        }
    });
    return "{\n".concat(pairs.join("\n"), "\n").concat(" ".repeat(indent - 2), "}");
}
exports.default = stringifyObject;
