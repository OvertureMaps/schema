import RemoteResolver from "@site/src/components/shared-libs/remoteResolver"
import YAMLFileResolver from "@site/src/components/shared-libs/yamlFileResolver"

type Params = {
  basePath?: string
  jsonPointer?: string
  remote?: boolean
  yamlBasePath?: string
}

export default function generateResolverOptions(params: Params) {
  const { basePath, jsonPointer, remote, yamlBasePath} = params

  let config = {}

  if (yamlBasePath || yamlBasePath == "") {
    config["resolvers"] = {
        file: YAMLFileResolver(yamlBasePath),
    }
  }

  if (remote) {
    if (config["resolvers"] === undefined) {
      config["resolvers"] = {}
    }
    config["resolvers"]["http"] = RemoteResolver("http")
    config["resolvers"]["https"] = RemoteResolver("https")
  }

  if (jsonPointer) {
    config["jsonPointer"] = jsonPointer
  }

  return config
}
