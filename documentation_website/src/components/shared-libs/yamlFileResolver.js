const yaml = require('js-yaml')
const YAML_FILES = require('@site/src/YAML_FILE_TREE.js').default

var generatePath = require("@site/src/components/shared-libs/generatePath");

Object.defineProperty(exports, "__esModule", { value: true });
function YAMLFileResolver(yamlPath) {
    if (yamlPath === void 0) { yamlPath = ""; }
    return {
        resolve: function (ref) {
            return new Promise(function (resolve, reject) {

                Promise.resolve().then(function () {

                    var relativeYamlPath = (0, generatePath.default)(ref, yamlPath);

                    if (YAML_FILES.hasOwnProperty(relativeYamlPath)){
                        var res = yaml.load(YAML_FILES[relativeYamlPath].default)
                        console.log("Found and returning " + relativeYamlPath)
                        return res
                    }else{
                        console.warn("Didn't find: " + relativeYamlPath)
                        return {}
                    }

                }).then(function (result) { return resolve(result)})
                .catch(function (err) { return reject(err); });
            });
        },
    };
}

exports.default = YAMLFileResolver;
