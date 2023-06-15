"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
function RemoteFileResolver(_type) {
    if (_type === void 0) { _type = "http"; }
    return {
        resolve: function (ref) {
            return new Promise(function (resolve, reject) {
                fetch(ref.toString(), {
                    headers: {
                        Accept: "application/json",
                    },
                })
                    .then(function (response) { return response.json(); })
                    .then(function (result) { return resolve(result); })
                    .catch(function (err) { return reject(err); });
            });
        },
    };
}
exports.default = RemoteFileResolver;
