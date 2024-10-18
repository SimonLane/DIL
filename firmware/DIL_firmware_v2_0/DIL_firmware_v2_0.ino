#include <Arduino.h>

// Function prototypes
void handleCommand1(int v1, int v2);
void handleCommand2(int v1);
void handleCommand3();

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;  // Wait for Serial to be ready
  }
  Serial.println("Teensy 4.1 ready to receive commands.");
}

void loop() {
  static String commandBuffer = "";

  // Read incoming serial data
  while (Serial.available() > 0) {
    char incomingByte = Serial.read();

    // Add the incoming character to the buffer
    commandBuffer += incomingByte;

    // Check if the command ends with a semicolon
    if (incomingByte == ';') {
      parseCommand(commandBuffer);
      commandBuffer = ""; // Clear buffer for the next command
    }
  }
}

void parseCommand(String command) {
  // Ensure the command starts with a forward slash
  if (command[0] != '/') {
    Serial.println("Invalid command format");
    return;
  }

  // Remove the forward slash and semicolon
  command.remove(0, 1);
  command.remove(command.length() - 1, 1);

  // Split the command into parts using '.' as the delimiter
  int firstDotIndex = command.indexOf('.');
  String word = command.substring(0, firstDotIndex);
  command.remove(0, firstDotIndex + 1);

  int values[4] = {0};
  int valueIndex = 0;
  while (command.length() > 0 && valueIndex < 4) {
    int dotIndex = command.indexOf('.');
    if (dotIndex == -1) {
      values[valueIndex] = command.toInt();
      command = "";
    } else {
      values[valueIndex] = command.substring(0, dotIndex).toInt();
      command.remove(0, dotIndex + 1);
    }
    valueIndex++;
  }

  // Determine which function to call based on the word
  if (word == "command1") {
    handleCommand1(values[0], values[1]);
  } else if (word == "command2") {
    handleCommand2(values[0]);
  } else if (word == "command3") {
    handleCommand3();
  } else {
    Serial.println("Unknown command");
  }
}

void handleCommand1(int v1, int v2) {
  Serial.print("Handling command1 with values: ");
  Serial.print(v1);
  Serial.print(", ");
  Serial.println(v2);
}

void handleCommand2(int v1) {
  Serial.print("Handling command2 with value: ");
  Serial.println(v1);
}

void handleCommand3() {
  Serial.println("Handling command3 with no values");
}

