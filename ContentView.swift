//ok so the ContentView dile defines the main UI for apps. It handles the layout and behaviour of the recording screen, including the display of recordins and the control buttons for starting and stopping recording
import SwiftUI

struct ContentView: View {
    
    @ObservedObject var audioRecorder: AudioRecorder
    
    var body: some View {//so, the body property defines the content and layout of a view. It uses NavigationView to allow anvigation and the title bar at the top.
        NavigationView {
            VStack {
                RecordingsList(audioRecorder: audioRecorder)//displays a list of recordings
                //below is the button styling
                if audioRecorder.recording == false {
                    Button(action: {self.audioRecorder.startRecording()}) {
                        Image(systemName: "circle.fill")
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 70, height: 70)
                            .clipped()
                            .foregroundColor(.red)
                            .padding(.bottom, 40)
                    }
                } else {
                    Button(action: {self.audioRecorder.stopRecording()}) {
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
            .navigationBarTitle("Voice Recorder")
            .navigationBarItems(trailing: EditButton())//places an edit button in the top-right corner of the navigation bar. It is handles by the RecordingsList view.
        }
    }
}

struct ContentView_Previews: PreviewProvider {//allows developers to see the UI without running the app. It passes a new instance of AudioRecorder for the preview
    static var previews: some View {
        ContentView(audioRecorder: AudioRecorder())
    }
}
