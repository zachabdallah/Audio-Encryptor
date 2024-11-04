//AppDelegate.swift is a key component of an IOS app that handles the app's lifecycle events, like launching, creating new scenes, and handling discarded scenes.It is a crucial part of aniOS apps architechture. A scene represents a single instance of an apps user interface and its associated state.
import UIKit

@UIApplicationMain//this attribute indicates that AppDelegate is the entry point of the app. it marks this class as responsible for setting up the app and managing its lifecycles. it tells the Swift compiler to generate a main function that runs the app, eliminating the need for an explicit main.swift file
class AppDelegate: UIResponder, UIApplicationDelegate {//AppDelegate is declared as a class and conforms to the UIApplicationDelegate protocol and inherits from UIResponder. This protocol defines methods for handling important app events, such as when the app launches, enters the background, or terminates. UIResponder allows the class to respond to and manage user events
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        //this method is called when the app has completedits launch process. it gievs you an opportunity to customize what happens when the app starts. in this case it returns true, which means the app successfully finished launching.
        return true
    }
    
    // MARK: UISceneSession Lifecycle
    
    func application(_ application: UIApplication, configurationForConnecting connectingSceneSession: UISceneSession, options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        // Called when a new scene session is being created, returning UISceneConfiguration which defines the role and behavior of the scene
        return UISceneConfiguration(name: "Default Configuration", sessionRole: connectingSceneSession.role)
    }
    
    func application(_ application: UIApplication, didDiscardSceneSessions sceneSessions: Set<UISceneSession>) {
        // Called when the user discards a scene session.
        // If any sessions were discarded while the application was not running, this will be called shortly after application:didFinishLaunchingWithOptions.
        // Use this method to release any resources that were specific to the discarded scenes, as they will not return.
    }
    
    
}

