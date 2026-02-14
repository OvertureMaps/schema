echo "Removing and re-fetching Overture documentation into docusaurus directory"
rm -rf docusaurus
git clone --depth=1 https://github.com/OvertureMaps/docs docusaurus

echo "Sym-linking examples docs into docusaurus"
ln -s $(pwd)/../examples $(pwd)/docusaurus/docs/_examples

echo "Sym-linking schema yaml into docusaurus"
ln -s $(pwd)/../schema $(pwd)/docusaurus/docs/_schema


echo "Sym-linking schema docs into docusaurus"
ln -s $(pwd)/schema $(pwd)/docusaurus/docs/schema

echo "Sym-linking taxonomy browser files into docusaurus"
ln -s $(pwd)/components/taxonomyBrowser.js $(pwd)/docusaurus/src/components/taxonomyBrowser.js
ln -s $(pwd)/css/taxonomyBrowser.css $(pwd)/docusaurus/src/css/taxonomyBrowser.css
ln -s $(pwd)/guides/places/taxonomy-browser.mdx $(pwd)/docusaurus/docs/guides/places/taxonomy-browser.mdx
ln -s $(pwd)/guides/places/overture-taxonomy-feb.csv $(pwd)/docusaurus/docs/guides/places/overture-taxonomy-feb.csv

echo "Adding taxonomy browser to sidebar"
sed -i '' "s|'guides/places/taxonomy',|'guides/places/taxonomy',\n            'guides/places/taxonomy-browser',|" $(pwd)/docusaurus/sidebars.js

cd docusaurus
npm install --prefer-dedupe

npm run docusaurus start
