// Example of basePath = '/schemas/examples/refs'
export default function generatePath(path: string, basePath: string = "") {
    const parts = path.toString().split("/")
    let finalPath = basePath

    for (let i = 0; i < parts.length; i++) {
      if (parts[i] === "..") {
        // Move up one directory in the base path
        finalPath = finalPath.split("/").slice(0, -1).join("/")
      } else if (parts[i] === ".") {
        // Ignore current directory notation
        continue
      } else {
        // Append the current directory to the base path
        finalPath = `${finalPath}/${parts[i]}`
      }
    }

    return finalPath
  }
