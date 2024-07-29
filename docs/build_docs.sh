echo "Removing and re-fetching Overture documentation into docusaurus directory"
rm -rf docusaurus
git clone --depth=1 https://github.com/OvertureMaps/docs docusaurus

echo "Sym-linking examples docs into docusaurus"
ln -s $(pwd)/../examples $(pwd)/docusaurus/docs/_examples

echo "Sym-linking schema yaml into docusaurus"
ln -s $(pwd)/../schema $(pwd)/docusaurus/docs/_schema


echo "Sym-linking schema docs into docusaurus"
ln -s $(pwd)/schema $(pwd)/docusaurus/docs/schema

cd docusaurus
npm install --prefer-dedupe

npm run docusaurus start
