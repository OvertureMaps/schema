export default function stringifyObject(obj: unknown, indent = 2): string {
    const keys = Object.keys(obj)
    const pairs = keys.map((key) => {
      const value = obj[key]
      if (typeof value === "function") {
        const match = value.toString().match(/function\s+([\w$]+)\s*\(([^)]*)\)/)
        const name = match ? match[1] : "anonymous"
        const params = match
          ? match[2]
              .split(",")
              .map((p) => p.trim())
              .join(", ")
          : ""
        return `${" ".repeat(
          indent,
        )}${key}: function ${name}(${params}) { /* function body */ },`
      } else if (
        typeof value === "object" &&
        !Array.isArray(value) &&
        value !== null
      ) {
        return `${" ".repeat(indent)}${key}: ${stringifyObject(
          value,
          indent + 2,
        )},`
      } else {
        return `${" ".repeat(indent)}${key}: ${JSON.stringify(value)},`
      }
    })
    return `{\n${pairs.join("\n")}\n${" ".repeat(indent - 2)}}`
  }
