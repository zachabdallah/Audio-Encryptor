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
                        // Stop recording and then show the password prompt
                        self.audioRecorder.stopRecording()
                        self.isPasswordPromptPresented = true
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
                PasswordPrompt(
                    isPresented: $isPasswordPromptPresented,
                    password: $currentPassword,
                    onSave: {
                        // Encrypt the last recording with the provided password
                        audioRecorder.encryptLastRecording(password: currentPassword)
                        currentPassword = "" // Reset the password
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
