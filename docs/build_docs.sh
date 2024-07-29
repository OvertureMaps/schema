echo "Removing and re-fetching Overture documentation into docusaurus directory"
rm -rf docusaurus
git clone --depth=1 https://github.com/OvertureMaps/docs docusaurus

echo "Copying Examples"
mkdir -p docusaurus/docs/_examples
cp -R ../examples/* docusaurus/docs/_examples/

echo "Copying Schema YAML"
mkdir -p docusaurus/docs/_schema
cp -R ../schema/* docusaurus/docs/_schema/

echo "Sym-linking schema docs into docusaurus"
ln -s $(pwd)/schema $(pwd)/docusaurus/docs/schema

cd docusaurus
npm install

npm run docusaurus start
