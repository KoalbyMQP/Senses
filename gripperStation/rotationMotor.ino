#include <Stepper.h>


const int stepsPerRevolution = 200; 

// Create a Stepper object. The motor’s 4 control pins are connected to Arduino pins 8, 9, 10, and 11.
Stepper motor(stepsPerRevolution, 8, 9, 10, 11);

// Keeps track of the current position (in steps) of the motor.
long currentPosition = 0;

void setup() {
    
  motor.setSpeed(8);   // Set the motor speed in revolutions per minute (RPM). Adjust this as needed.
  Serial.begin(9600);   // Initialize serial communication at 9600 baud.
  
  // Inform that the Arduino is ready to receive commands.
  Serial.println("Ready. Send command: 'GRIPPER <number>' where number is between 0 and 12 (0 = home).");
}

void loop() {
  // Check if there is serial data available.
  if (Serial.available() > 0) {
    // Read the incoming command until a newline character is encountered.
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove any leading/trailing whitespace.
    
    // Print out the received command for debugging purposes.
    Serial.print("Received command: ");
    Serial.println(command);
    
    // Check if the command starts with "GRIPPER".
    if (command.startsWith("GRIPPER")) {
      // Find the index of the space after "GRIPPER".
      int spaceIndex = command.indexOf(' ');
      if (spaceIndex != -1) {
        // Extract the number part of the command.
        String numberStr = command.substring(spaceIndex + 1);
        int input = numberStr.toInt();
        
        // Validate that the input number is within the expected range.
        if (input >= 0 && input <= 12) {
          // Map the input number to a target step position.
          // For example, if stepsPerRevolution is 200, then input 12 maps to 200 steps (one full revolution).
          long targetPosition = map(input, 0, 12, 0, stepsPerRevolution);
          
          Serial.print("Targeting step position: ");
          Serial.println(targetPosition);
          
          // Calculate how many steps are needed to reach the target position.
          long steps = targetPosition - currentPosition;
          
          Serial.print("Calculated steps to move: ");
          Serial.println(steps);
          
          // Command the motor to move the calculated number of steps.
          motor.step(steps);
          Serial.println("Movement complete.");
          
          // Update the current position.
          currentPosition = targetPosition;
        } else {
          Serial.println("Error: Number out of range. Please send a number between 0 and 12.");
        }
      } else {
        Serial.println("Error: Invalid command format. Expected 'GRIPPER <number>'.");
      }
    } else {
      Serial.println("Error: Unknown command. Please send a command starting with 'GRIPPER'.");
    }
  }
}
