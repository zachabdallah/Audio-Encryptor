import SwiftUI

struct PasswordPrompt: View {
    @Binding var isPresented: Bool
    @Binding var password: String
    let onSave: () -> Void
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Enter Password")
                .font(.headline)
            
            SecureField("Password", text: $password)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .padding()
            
            HStack {
                Button("Cancel") {
                    isPresented = false
                }
                .foregroundColor(.red)
                
                Button("Submit") {
                    onSave()
                    isPresented = false
                }
                .foregroundColor(.blue)
            }
        }
        .padding()
        .background(Color.white)
        .cornerRadius(10)
        .shadow(radius: 10)
    }
}

