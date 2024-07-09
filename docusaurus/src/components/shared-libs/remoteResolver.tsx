type Param = "http" | "https"

export default function LocalFileResolver(_type: Param = "http") {
  return {
    resolve: (ref: string) => {
      return new Promise((resolve, reject) => {
        fetch(ref.toString(), {
          headers: {
            Accept: "application/json",
          },
        })
          .then((response) => response.json())
          .then((result) => resolve(result))
          .catch((err) => reject(err))
      })
    },
  }
}
