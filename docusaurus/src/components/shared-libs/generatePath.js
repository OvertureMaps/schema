"use strict";
Object.defineProperty(exports, "__esModule", { value: true });

function generatePath(path, basePath) {
    if (basePath === void 0) { basePath = ""; }
    var parts = path.toString().split("/");

    var finalPath = basePath;
    for (var i = 0; i < parts.length; i++) {
        if (parts[i] === "..") {
            // Move up one directory in the base path
            finalPath = finalPath.split("/").slice(0, -1).join("/");
        }
        else if (parts[i] === ".") {
            // Ignore current directory notation
            continue;
        }
        else {
            // Append the current directory to the base path
            finalPath = "".concat(finalPath, "/").concat(parts[i]);
        }
    }
    return finalPath;
}
exports.default = generatePath;
