const path = require('path')
module.exports = {
  plugins: [
    require('postcss-import')({
      resolve(id, basedir, importOptions) {
        if (id.startsWith('~@')) {
          return path.resolve(process.env.UNI_INPUT_DIR || process.cwd(), id.substr(2))
        } else if (id.startsWith('~')) {
          return path.resolve(process.env.UNI_INPUT_DIR || process.cwd(), 'node_modules', id.substr(1))
        }
        return path.resolve(basedir, id)
      }
    }),
    require('@dcloudio/vue-cli-plugin-uni/packages/postcss'),
  ]
}