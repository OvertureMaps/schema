const yaml = require('js-yaml')

const YAML_FILES = {
    '/addresses/address.yaml' : require('!!raw-loader!@site/docs/yaml/addresses/address.yaml'),

    '/admins/administrativeBoundaries.yaml' : require('!!raw-loader!@site/docs/yaml/admins/administrativeBoundary.yaml'),
    '/admins/defs.yaml' : require('!!raw-loader!@site/docs/yaml/admins/defs.yaml'),
    '/admins/locality.yaml' : require('!!raw-loader!@site/docs/yaml/admins/locality.yaml'),

    '/buildings/footprint.yaml' : require('!!raw-loader!@site/docs/yaml/buildings/footprint.yaml'),

    '/places/place.yaml' : require('!!raw-loader!@site/docs/yaml/places/place.yaml'),

    '/transportation/connector.yaml' : require('!!raw-loader!@site/docs/yaml/transportation/connector.yaml'),
    '/transportation/segment.yaml' : require('!!raw-loader!@site/docs/yaml/transportation/segment.yaml'),

    '/defs.yaml' : require('!!raw-loader!@site/docs/yaml/defs.yaml'),
    '/schema.yaml' : require('!!raw-loader!@site/docs/yaml/schema.yaml')
}

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
