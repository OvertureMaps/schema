"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var localFileResolver_1 = require("@site/src/components/shared-libs/localFileResolver");
var remoteResolver_1 = require("@site/src/components/shared-libs/remoteResolver");
function generateResolverOptions(params) {
    var basePath = params.basePath, jsonPointer = params.jsonPointer, remote = params.remote;
    var config = {};
    if (basePath) {
        config["resolvers"] = {
            file: (0, localFileResolver_1.default)(basePath),
        };
    }
    if (remote) {
        if (config["resolvers"] === undefined) {
            config["resolvers"] = {};
        }
        config["resolvers"]["http"] = (0, remoteResolver_1.default)("http");
        config["resolvers"]["https"] = (0, remoteResolver_1.default)("https");
    }
    if (jsonPointer) {
        config["jsonPointer"] = jsonPointer;
    }
    return config;
}
exports.default = generateResolverOptions;
