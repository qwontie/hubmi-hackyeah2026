const { withAppDelegate, withInfoPlist } = require("expo/config-plugins");

const SCENE_MANIFEST = {
  UIApplicationSupportsMultipleScenes: false,
  UISceneConfigurations: {
    UIWindowSceneSessionRoleApplication: [
      {
        UISceneConfigurationName: "Default Configuration",
        UISceneDelegateClassName: "EXExpoAppSceneDelegate",
      },
    ],
  },
};

const WINDOW_START =
  /#if os\(iOS\) \|\| os\(tvOS\)\s*window = UIWindow\(frame: UIScreen\.main\.bounds\)[\s\S]*?#endif\s*/;

const adoptScenes = (source) =>
  source
    .replace(
      "class AppDelegate: ExpoAppDelegate {",
      "class AppDelegate: ExpoAppDelegate, ExpoReactNativeFactoryProvider {"
    )
    .replace(WINDOW_START, "");

module.exports = (config) => {
  const withPlist = withInfoPlist(config, (next) => {
    next.modResults.UIApplicationSceneManifest = SCENE_MANIFEST;
    return next;
  });
  return withAppDelegate(withPlist, (next) => {
    if (next.modResults.language === "swift") {
      next.modResults.contents = adoptScenes(next.modResults.contents);
    }
    return next;
  });
};
