var localFileResolver = require("@site/src/components/shared-libs/localFileResolver");
var remoteResolver = require("@site/src/components/shared-libs/remoteResolver");
var yamlFileResolver  = require("@site/src/components/shared-libs/yamlFileResolver");

Object.defineProperty(exports, "__esModule", { value: true });
function generateResolverOptions(params) {
    var basePath = params.basePath, jsonPointer = params.jsonPointer, remote = params.remote, yamlPath = params.yamlBasePath;
    var config = {};
    if (yamlPath || yamlPath == "") {
        config["resolvers"] = {
            file: (0, yamlFileResolver.default)(yamlPath),
        }
    }
    if (basePath) {
        config["resolvers"] = {
            file: (0, localFileResolver.default)(basePath),
        };
    }
    if (remote) {
        if (config["resolvers"] === undefined) {
            config["resolvers"] = {};
        }

        config["resolvers"]["http"] = (0, remoteResolver.default)("http");
        config["resolvers"]["https"] = (0, remoteResolver.default)("https");
    }
    if (jsonPointer) {
        config["jsonPointer"] = jsonPointer;
    }
    return config;
}
exports.default = generateResolverOptions;
