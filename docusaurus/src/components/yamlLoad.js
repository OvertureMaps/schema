Object.defineProperty(exports, "__esModule", { value: true });

yaml = require('js-yaml')

function yamlLoad(string){
    return yaml.load(string)
}

exports.default = yamlLoad;
