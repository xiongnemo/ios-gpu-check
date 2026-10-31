#!/bin/bash
# GPUCheck.ipa, not signed by Apple: for an iOS that installs apps without Apple's signature (the K40 port), or for
# whatever re-signs it to put it on an iPhone.
#   macOS:      ./build.sh                      (Xcode's clang and iPhoneOS SDK, through xcrun)
#   elsewhere:  CC=<a clang that targets iOS and links with ld64> SDK=<an iPhoneOS SDK> ./build.sh
#               e.g. CC=xnu-clang SDK=$THEOS/sdks/iPhoneOS16.5.sdk
# OUT=DIR (default build/): DIR/Payload/GPUCheck.app and DIR/GPUCheck.ipa.
# With ldid on PATH (or LDID=another one) the program is signed with Entitlements.plist (which asks for nothing: an
# ad-hoc signature); without it, it keeps whatever signature the linker gave it.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$HERE/build}
if [ -z "${SDK:-}" ] && command -v xcrun >/dev/null 2>&1; then
	SDK=$(xcrun --sdk iphoneos --show-sdk-path)
	CC=${CC:-$(xcrun --sdk iphoneos --find clang)}
fi
: "${SDK:?SDK: an iPhoneOS SDK (on macOS xcrun finds it)}"
CC=${CC:-clang}
LDID=${LDID:-ldid}
APP=$OUT/Payload/GPUCheck.app

rm -rf "$OUT/Payload" "$OUT/GPUCheck.ipa"
mkdir -p "$APP"
# (-target, not -arch and -miphoneos-version-min: a wrapper such as xnu-clang puts its own -target ios16.5 first, which
# wins over -miphoneos-version-min, and the program would then ask for iOS 16.5; the last -target is the one that counts)
# (OpenGLES linked by the program itself, not only through GLKit: the K40 port gives an application the GPU's OpenGL ES
# only when its main binary loads OpenGLES.framework. Metal, SpriteKit and SceneKit weakly: where one is missing, the
# application still starts and that test says so.)
$CC -target arm64-apple-ios15.0 -isysroot "$SDK" -O1 -fobjc-arc \
	-framework UIKit -framework Foundation -framework CoreFoundation -framework CoreGraphics -framework QuartzCore \
	-framework OpenGLES -framework GLKit -framework CoreImage \
	-weak_framework Metal -weak_framework SpriteKit -weak_framework SceneKit \
	-o "$APP/GPUCheck" "$HERE/main.m"
if command -v "$LDID" >/dev/null 2>&1; then
	sed 's/\r$//' "$HERE/Entitlements.plist" > "$OUT/Entitlements.plist"
	"$LDID" -S"$OUT/Entitlements.plist" "$APP/GPUCheck"
	echo "build.sh: signed by $LDID with Entitlements.plist"
fi
sed 's/\r$//' "$HERE/Info.plist" > "$APP/Info.plist"
python3 -I "$HERE/mkicon.py" "$APP"
printf 'APPL????' > "$APP/PkgInfo"
(cd "$OUT" && python3 -c "import shutil; shutil.make_archive('GPUCheck', 'zip', '.', 'Payload')" && mv GPUCheck.zip GPUCheck.ipa)
ls -l "$OUT/GPUCheck.ipa"
