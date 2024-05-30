import generatePath from "@site/src/components/shared-libs/generatePath";
import yaml from "js-yaml";

const schemaYamlFiles = require.context('@site/docs/_schema', true, /\.(yaml|yml)$/);
var preloadedYamlSchema = {}

schemaYamlFiles.keys().forEach(function(path){
    preloadedYamlSchema[path.replace('./', '/')] = yaml.load(
      require('!!raw-loader!@site/docs/_schema' + path.replace('./', '/')).default
    );
})

export default function YAMLFileResolver(basePath: string = "") {
    return {
      resolve: (ref: string) => {
        return new Promise((resolve, reject) => {

          Promise.resolve().then(function(){

            var relativeYamlPath = generatePath(ref, basePath)

            if (preloadedYamlSchema.hasOwnProperty(relativeYamlPath)){
              return preloadedYamlSchema[relativeYamlPath];
            }else{
              return {}
            }
          }).then(function(result){ return resolve(result)}
          ).catch(function(err){ return reject(err); });
        });
      }
    }
  }
