//this file has two views that work together to display a list of audio recordiggs and probide playback controls for each recording.
import SwiftUI

struct RecordingsList: View {
    @ObservedObject var audioRecorder: AudioRecorder
    
    var body: some View {
        List {
            ForEach(audioRecorder.recordings.filter { FileManager.default.fileExists(atPath: $0.fileURL.path) }, id: \.fileURL) { recording in
                RecordingRow(audioURL: recording.fileURL, audioRecorder: audioRecorder)
            }


            .onDelete(perform: delete)
        }
    }
    
    func delete(at offsets: IndexSet) {
        var urlsToDelete = [URL]()
        for index in offsets {
            urlsToDelete.append(audioRecorder.recordings[index].fileURL)
        }
        audioRecorder.deleteRecording(urlsToDelete: urlsToDelete)
    }
}


struct RecordingRow: View {
    var audioURL: URL
    @ObservedObject var audioPlayer = AudioPlayer()
    @ObservedObject var audioRecorder: AudioRecorder
    
    @State private var isPasswordPromptPresented = false
    @State private var currentPassword = ""
    
    var body: some View {
        HStack {
            Text(audioURL.lastPathComponent)
            Spacer()
            if audioPlayer.isPlaying == false {
                Button(action: {
                    self.audioPlayer.startPlayback(audio: self.audioURL)
                }) {
                    Image(systemName: "play.circle")
                        .imageScale(.large)
                }
            } else {
                Button(action: {
                    self.audioPlayer.stopPlayback()
                }) {
                    Image(systemName: "stop.fill")
                        .imageScale(.large)
                }
            }
            Button(action: {
                self.isPasswordPromptPresented = true // Show password prompt for decryption
            }) {
                Image(systemName: "lock.open")
                    .imageScale(.large)
                    .foregroundColor(.blue)
            }
        }
        .sheet(isPresented: $isPasswordPromptPresented) {
            PasswordPrompt(
                isPresented: $isPasswordPromptPresented,
                password: $currentPassword,
                onSave: {
                    audioRecorder.decryptAudio(fileURL: audioURL, password: currentPassword) { decryptedFileURL in
                        if let decryptedFileURL = decryptedFileURL {
                            self.audioPlayer.startPlayback(audio: decryptedFileURL)
                        } else {
                            print("Failed to decrypt audio.")
                        }
                        currentPassword = ""
                    }
                }
            )
        }
    }
}


struct RecordingsList_Previews: PreviewProvider {
    static var previews: some View {
        RecordingsList(audioRecorder: AudioRecorder())
    }
}
