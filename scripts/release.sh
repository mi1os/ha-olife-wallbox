#!/bin/bash

set -e

# Check if version is provided
if [ -z "$1" ]; then
    echo "Please provide a version number (e.g. ./release.sh 0.2.1)"
    exit 1
fi

VERSION=$1
VERSION_WITHOUT_V=$(echo $VERSION | sed 's/^v//')

# Check if version starts with v, if not add it for the tag
if [[ $VERSION != v* ]]; then
    TAG_VERSION="v$VERSION"
else
    TAG_VERSION=$VERSION
    VERSION_WITHOUT_V=$(echo $VERSION | sed 's/^v//')
fi

echo "Preparing release $VERSION_WITHOUT_V (tag: $TAG_VERSION)"

# Update version in manifest.json
sed -i.bak "s/\"version\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"version\": \"$VERSION_WITHOUT_V\"/" custom_components/olife_wallbox/manifest.json
rm custom_components/olife_wallbox/manifest.json.bak

# Create zip file with proper structure for HACS
echo "Creating zip file with proper structure for HACS..."
rm -f olife_wallbox.zip

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
mkdir -p $TEMP_DIR/custom_components

# Copy files to the temp directory with the proper structure
cp -r custom_components/olife_wallbox $TEMP_DIR/custom_components/
cp README.md $TEMP_DIR/

# Create the zip file from the temp directory
cd $TEMP_DIR
zip -r $OLDPWD/olife_wallbox.zip .
cd $OLDPWD

# Clean up
rm -rf $TEMP_DIR

# Commit changes
echo "Committing changes..."
git add custom_components/olife_wallbox/manifest.json
git commit -m "Bump version to $VERSION_WITHOUT_V"

# Create tag
echo "Creating tag..."
git tag -a $TAG_VERSION -m "Release $TAG_VERSION"

echo ""
echo "Release preparation complete!"
echo ""
echo "To finish the release process:"
echo "1. Run: git push origin main"
echo "2. Run: git push origin $TAG_VERSION"
echo ""
echo "GitHub Actions will automatically create the release and attach the zip file." 