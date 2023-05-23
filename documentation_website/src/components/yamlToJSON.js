Object.defineProperty(exports, "__esModule", { value: true });

yaml = require('js-yaml')

function yamlToJSON(string){

    res = yaml.load(string)

    return res
}

exports.default = yamlToJSON;
