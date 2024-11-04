//define an extension for the Date type. Extensions allow you to add new functionality to existing types without modifying its original implementation. Here it allows ant Date instance to be easily transformed into a string based on a custom date format
import Foundation

extension Date
{
    func toString(dateFormat format: String ) -> String
    {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = format
        return dateFormatter.string(from: self)
    }
    
}
