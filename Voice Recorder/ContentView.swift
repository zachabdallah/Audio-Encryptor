import SwiftUI

struct ContentView: View {
    @ObservedObject var audioRecorder: AudioRecorder
    @State private var isPasswordPromptPresented = false
    @State private var currentPassword = ""
    
    var body: some View {
        NavigationView {
            VStack {
                RecordingsList(audioRecorder: audioRecorder)
                
                if audioRecorder.recording == false {
                    Button(action: {
                        self.audioRecorder.startRecording()
                    }) {
                        Image(systemName: "circle.fill")
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 70, height: 70)
                            .clipped()
                            .foregroundColor(.red)
                            .padding(.bottom, 40)
                    }
                } else {
                    Button(action: {
                        self.audioRecorder.stopRecording()
                        isPasswordPromptPresented = true // Show password prompt after stopping
                    }) {
                        Image(systemName: "stop.fill")
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 70, height: 70)
                            .clipped()
                            .foregroundColor(.red)
                            .padding(.bottom, 40)
                    }
                }
            }
            .navigationBarTitle("Sub 2")
            .navigationBarItems(trailing: EditButton())
            .overlay(
                // Show password prompt as an overlay
                PasswordPrompt(
                    isPresented: $isPasswordPromptPresented,
                    password: $currentPassword,
                    onSave: {
                        audioRecorder.password = currentPassword
                        if let lastRecording = audioRecorder.recordings.last {
                            audioRecorder.uploadWAVFile(fileURL: lastRecording.fileURL, password: currentPassword)
                        }
                        currentPassword = ""
                    }
                )
                .frame(width: 300, height: 200)
                .background(Color.black.opacity(isPasswordPromptPresented ? 0.3 : 0))
                .opacity(isPasswordPromptPresented ? 1 : 0)
            )
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView(audioRecorder: AudioRecorder())
    }
}
