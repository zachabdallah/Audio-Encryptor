import Foundation//basic functionalities like working with strings, file management, etc
import SwiftUI
import Combine//used for binding data
import AVFoundation//framework for handling audio functionalities like recording and playback
//file that manages the recording of audio and recordings. It also integrates encryption and decryption functionality.
class AudioRecorder: NSObject, ObservableObject {// AudioRecorder is inheriting from NSObject which is required for working with AVfoundation and it conforms to ObservableObject, which means that it can be used by SwiftUI to trigger UI updates.
    @Published var password: String = ""//when something is @Published, any changes will trigger a view update
    let objectWillChange = PassthroughSubject<AudioRecorder, Never>()//this is now a Combine subject that notifies SwiftUI of updates
    
    var audioRecorder: AVAudioRecorder!
    var recordings = [Recording]()//we define the Recording data model in another file
    var recording = false {
        didSet {
            objectWillChange.send(self)//didSet is an observer that sends an update when the signal changes
        }
    }
    
    override init() {//initialize the class and fetch existing recordings from the file system
        super.init()
        fetchRecordings()
    }
    //lets start
    func startRecording() {
        let recordingSession = AVAudioSession.sharedInstance()//start session
        
        //activate sesion for audio capture
        do {
            try recordingSession.setCategory(.playAndRecord, mode: .default)
            try recordingSession.setActive(true)
        } catch {
            print("Failed to set up recording session: \(error.localizedDescription)")
        }
        
        
        //paths
        let documentPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let audioFilename = documentPath.appendingPathComponent("recording_\(UUID().uuidString).wav")
        
        //format
        let settings = [
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 2,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ] as [String : Any]
        //init audioRecorder with the file location and settings and starts recording. Updates recording to true
        do {
            audioRecorder = try AVAudioRecorder(url: audioFilename, settings: settings)
            audioRecorder.record()
            
            recording = true
            print("Recording started at: \(audioFilename)")
        } catch {
            print("Could not start recording: \(error.localizedDescription)")
        }
    }
    
    func stopRecording() {
        audioRecorder.stop()
        audioRecorder = nil
        recording = false
        fetchRecordings()
    }
    
    func encryptLastRecording(password: String) {
        //this just makes sure there's an existing recording to encrypt
        guard let lastRecording = recordings.last else {
            print("No recordings available for encryption.")
            return
        }
        //if the password is empty, the last recording is deleted
        if password.isEmpty {
            print("Password input canceled. Deleting original file.")
            do {
                try FileManager.default.removeItem(at: lastRecording.fileURL)
                print("Original file deleted after cancellation: \(lastRecording.fileURL)")
                fetchRecordings()
            } catch {
                print("Failed to delete original file: \(error)")
            }
            return
        }
        //ecrypt here
        encryptAndStoreAudio(fileURL: lastRecording.fileURL, password: password)
    }


    
    func encryptAndStoreAudio(fileURL: URL, password: String) {
        encryptAudio(fileURL: fileURL, password: password) { encryptedFileURL in
            if let encryptedFileURL = encryptedFileURL {
                do {
                    //update recording entries
                    if FileManager.default.fileExists(atPath: fileURL.path) {
                        try FileManager.default.removeItem(at: fileURL)
                        print("Original file deleted: \(fileURL)")
                    } else {
                        print("Original file not found for deletion: \(fileURL)")
                    }
                    
                    try FileManager.default.moveItem(at: encryptedFileURL, to: fileURL)
                    print("Encrypted file moved to: \(fileURL)")
                    
                    DispatchQueue.main.async {
                        self.fetchRecordings()
                    }
                    //
                } catch {
                    print("Error during file replacement: \(error)")
                }
            } else {
                print("Encryption failed: No encrypted file returned.")
            }
        }
    }
    
    func encryptAudio(fileURL: URL, password: String, completion: @escaping (URL?) -> Void) {
        //provide a POST request to upload the audio file and password to our Flask server
        uploadWAVFile(fileURL: fileURL, password: password, endpoint: "encrypt", completion: completion)
    }
    func decryptAudio(fileURL: URL, password: String, completion: @escaping (URL?) -> Void) {
        //same thing here, but it communicates with a different part of the server
        uploadWAVFile(fileURL: fileURL, password: password, endpoint: "decrypt") { decryptedFileURL in
            if let decryptedFileURL = decryptedFileURL {
                print("Decrypted audio available at: \(decryptedFileURL)")
                completion(decryptedFileURL)
            } else {
                print("Decryption failed.")
                completion(nil)
            }
        }
    }
    
    func uploadWAVFile(fileURL: URL, password: String, endpoint: String, completion: @escaping (URL?) -> Void) {
        //this whole function prepares the POST request to be completely accurate and readabe to our Flask server.
        guard let serverURL = URL(string: "http://127.0.0.1:5000/\(endpoint)") else {
            print("Invalid server URL.")
            completion(nil)
            return
        }
        
        var request = URLRequest(url: serverURL)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        
        
        if let wavData = try? Data(contentsOf: fileURL) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileURL.lastPathComponent)\"\r\n".data(using: .utf8)!)
            body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
            body.append(wavData)
            body.append("\r\n".data(using: .utf8)!)
        }
        
        
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"password\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(password)\r\n".data(using: .utf8)!)
        
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        
        let task = URLSession.shared.uploadTask(with: request, from: body) { data, response, error in
            if let error = error {
                print("Upload error: \(error)")
                completion(nil)
                return
            }
            
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                guard let data = data else {
                    print("No data returned from server.")
                    completion(nil)
                    return
                }
                
                let tempPath = FileManager.default.temporaryDirectory.appendingPathComponent("\(endpoint)_audio.wav")
                do {
                    try data.write(to: tempPath)
                    print("\(endpoint.capitalized) audio saved at: \(tempPath)")
                    completion(tempPath)
                } catch {
                    print("Failed to save \(endpoint) audio: \(error)")
                    completion(nil)
                }
            }
            if let httpResponse = response as? HTTPURLResponse {
                print("Server error: \(httpResponse.statusCode)")
            } else {
                print("Server error: Unknown status code.")
            }

        }
        
        task.resume()
    }
    
    func fetchRecordings() {
        recordings.removeAll()
        
        let fileManager = FileManager.default
        let documentDirectory = fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
        
        do {
            let directoryContents = try fileManager.contentsOfDirectory(at: documentDirectory, includingPropertiesForKeys: nil)
            
            for audio in directoryContents {
                if fileManager.fileExists(atPath: audio.path) {
                    print("Adding file to recordings: \(audio.lastPathComponent)")
                    let recording = Recording(fileURL: audio, createdAt: getFileDate(for: audio))
                    recordings.append(recording)
                } else {
                    print("Skipping non-existent file: \(audio.lastPathComponent)")
                }
            }
            
            recordings.sort(by: { $0.createdAt.compare($1.createdAt) == .orderedAscending })
        } catch {
            print("Failed to fetch recordings: \(error)")
        }
        
        objectWillChange.send(self)
    }


    
    func deleteRecording(urlsToDelete: [URL]) {
        for url in urlsToDelete {
            do {
                try FileManager.default.removeItem(at: url)
                print("Deleted file: \(url)")
            } catch {
                print("File could not be deleted: \(error.localizedDescription)")
            }
        }
        fetchRecordings()
    }

}
