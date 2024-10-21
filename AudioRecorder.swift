//so this file lets the user record audio, save it as a .wav file, display recorded files, delete recordings, and upload audio files to a Flask server for processing in a python script
import Foundation
import SwiftUI
import Combine
import AVFoundation

class AudioRecorder: NSObject, ObservableObject {//this class manages all the functionality related to audio recording, managing files, and uploading recordings to a server. Since it conforms to the ObservableObject protocol, its able to send changes to the SwiftUI view so that the user can see changes in real-time. Also, NSObject is the base (parent) class that is necessary for interacting with AVFoundations API.
    
    override init() {//this is the initializer for the class. It calls fetchRecording() to retrieve any previously saved audio files and make them available when the app starts.
        super.init()//calls the init of the parent class (NSObject)
        fetchRecording()
    }
    
    let objectWillChange = PassthroughSubject<AudioRecorder, Never>()//So, a PassthroughIObject (this one updates of type AudioRecorder and never fails) is used to notify SwiftUI whenever changes occur in the class, such as recording stopping or starting. This triggers updates to the UI. objectWillChange is a Combine object that signals the SwiftUI view when changes occur, forcing the view to update.
    
    var audioRecorder: AVAudioRecorder!//This is a reference to the AVAudioRecorder object, which will handle the actual recording. The '!' means it will be assigned later.
    
    var recordings = [Recording]()//this is an array that stores Recording objects. Each Recording contains the file URL and timestamp of an audio recording.
    
    var recording = false {//this is just a book indicating whether a recording is in progress
        didSet {//so this block runs whenever 'recording' is updated. It triggers the UI to update by sending a notification to objectWillChange (red circle -> square circle for example)
            objectWillChange.send(self)
        }
    }
    
    func startRecording() {//ok so this function actually initiates an audio recording session
        let recordingSession = AVAudioSession.sharedInstance()//
        do {
            try recordingSession.setCategory(.playAndRecord, mode: .default)//configures the session to allow both playback and recording
            try recordingSession.setActive(true)//activates the session
        } catch {
            print("Failed to set up recording session")
        }
        
        let documentPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]//retrieve document directory where the audio file will be saved
        let audioFilename = documentPath.appendingPathComponent("\(Date().toString(dateFormat: "dd-MM-YY 'at' HH:mm:ss")).wav")//this generates a unique .wav file based on the current date and time
        
        let settings = [//this is just setting the proper encoding values for when we get the audio in
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 2,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ] as [String : Any]
        
        do {
            audioRecorder = try AVAudioRecorder(url: audioFilename, settings: settings)//create an AVAudioRecorder instance with the specified filename and settings
            audioRecorder.record()//start recording:P
            
            recording = true//updates the state. SwiftUI should go up and re-evaluate that didSet{} block up there to update the UI again now
            print("Recording started at: \(audioFilename)")
        } catch {
            print("Could not start recording: \(error.localizedDescription)")
        }
    }
    
    func stopRecording() {
        audioRecorder.stop()//stop recording audio
        recording = false//update state
        
        fetchRecording()//refresh list of saved recordings
        
        // now we pass the WAV file to the Python script after stopping the recording
        if let lastRecording = recordings.last {
            uploadWAVFile(fileURL: lastRecording.fileURL)//upload the latest recording to the server
        }
    }
    
    func uploadWAVFile(fileURL: URL) {//send the recorded file to a server using a "POST request". It encodes the audio file into a "multipart/form-data" format, which is used when sending files in a web request.
        let url = URL(string: "http://127.0.0.1:5000/analyze")!//so this creates a URL object point at 127.0.0.1 (which is localhost, the server running on the same machine). the /analyze path is the endpoint on the server responsible for handling the file you send.
        var request = URLRequest(url: url)//creates an HTTP request object which holds the url information
        request.httpMethod = "POST"//we're senging files in a POST request. This is just a method of sending data to a web server to create or update a resource, and it's commonly used to submit and upload stuff. We're doing this because we will eventually get something back: our encrypted audio.
        
        let boundary = UUID().uuidString//a boundary is a unique identifier (a random string generated using UUID().uuidString) that separates different parts of the request body. It's important for multipart/form-data requests because it marks where each part begins and ends. multipart/form-data is a special encoding type used to send files or binary data over the web. So now when we set it to "Content-Type" below, the server knows to expect a file upload not a binary.
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")//boundary =(boundary) tells the server where each part of the file starts and ends.
        
        var body = Data()//create an empty Data object which will hold the body of the request.
        
        if let wavData = try? Data(contentsOf: fileURL) {//this reads the contents of the .wav file from the fileURL, which is the path to the audio file we just recorded
            body.append("--\(boundary)\r\n".data(using: .utf8)!)//add the first boundary to separate parts of the data. start with "--" then the boundary string
            body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileURL.lastPathComponent)\"\r\n".data(using: .utf8)!)//this describres the "form-data" part, where we put the name of the field in the form and then the actual filename
            body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)//specifies audio and wav file
            body.append(wavData)
            body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)//close the body by appending the final boundary and then "--", signaling the end of the data
        }
        
        let task = URLSession.shared.uploadTask(with: request, from: body)//this creates a network task that uploads the file to the server. It uses the request object and the body containing the file data.
        {
            data, response, error in
            if let error = error {
                print("Upload error: \(error)")
                return
            }
            
            if let response = response as? HTTPURLResponse {//check server response. if the upload is successful, a 200 status code will be reeived and printed here
                if response.statusCode == 200 {
                    print("File uploaded and processed successfully!")
                } else {
                    print("Server error with status code: \(response.statusCode)")
                }
            }
        }
        
        task.resume()//start the task tio send the request and upload the file to the sever
        //notes:
        //multipart form data is a way to send large amounts of binaryc data in a POST request. Each part of ther data (file, headers, etc.) is separated by a boundary. The request is formatted to include metadata (like Content-Disposition) to tell the server what each part of the data represents.
        //The UUID boundary (the random string) serves as a marker to separate different parts of the bofdy. It's crucial for the server to properly parse and handle each part of the form data.
        //We'll probably use something like a GET request when we want the data back, because POST is not usually for sending AND getting.
    }

    
    func fetchRecording() {//retrieve all audio recordings saved in the app
        recordings.removeAll()
        
        let fileManager = FileManager.default//use the default file system to access stored files
        let documentDirectory = fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let directoryContents = try! fileManager.contentsOfDirectory(at: documentDirectory, includingPropertiesForKeys: nil)
        for audio in directoryContents {
            let recording = Recording(fileURL: audio, createdAt: getFileDate(for: audio))
            recordings.append(recording)
        }
        
        recordings.sort(by: { $0.createdAt.compare($1.createdAt) == .orderedAscending})
        
        objectWillChange.send(self)//update state to notify UI of changes
    }
    
    func deleteRecording(urlsToDelete: [URL]) {
        for url in urlsToDelete {
            print(url)
            do {
                try FileManager.default.removeItem(at: url)
            } catch {
                print("File could not be deleted!")
            }
        }
        fetchRecording()
    }
}
