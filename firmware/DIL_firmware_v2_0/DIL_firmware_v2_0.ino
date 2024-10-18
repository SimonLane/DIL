#include <Arduino.h>

// Function prototypes
void handleCommand1(int v1, int v2);
void handleCommand2(int v1);
void handleCommand3();

#include <SPI.h>

//galvos
const byte CS     = 12; 
const byte CLOCK  = 13;
const byte DATA   = 11;
//stage
const byte Xo     = 31;
const byte Yo     = 29;
const byte Zo     = 27;
const byte Xi     = 32;
const byte Yi     = 30;
const byte Zi     = 28;

//digital I/O
const byte CamOut               = 23;
const byte CamIn                = 22;
const byte trigger_LED          = 16;
const byte trigger_Filter       = 40;
const byte trigger_Laser        = 35;

volatile bool stage_ready_flag  = true;     // flag denoting when stage moves are complete
volatile bool cam_ready_flag    = true;     // flag denotes when camera has returned a 'readout complete' signal
const float firmware            = 2.0;      // firmware version

uint16_t slice_counter          = 0;        // for tracking slices through a z-stack
uint16_t nZ                     = 0;        // for storing total number of slices in a z-stack
bool z_stacking                 = false;    // flag denotes when z-stack is taking place
bool scanning                   = false;    // flag denotes when continuous scanning is taking place

const byte HALF_CLOCK_PERIOD    = 1;        // 2 uS of clock period 

void setup() {
  Serial.begin(115200);
  while (!Serial) {;}  // Wait for Serial to be ready
  Serial.println("DIL ready to receive commands.");
  SPI.begin();
//  pinMode(DATA, OUTPUT);
//  pinMode(CLOCK, OUTPUT);
  pinMode(CS, OUTPUT);
  digitalWrite(CS, HIGH);
//  digitalWrite(DATA, LOW);
//  digitalWrite(CLOCK, LOW);
  pinMode(Xo, OUTPUT);
  pinMode(Yo, OUTPUT);
  pinMode(Zo, OUTPUT);
  pinMode(Xi, INPUT_PULLUP);
  pinMode(Yi, INPUT_PULLUP);
  pinMode(Zi, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(Zi), z_move_complete, FALLING);
  
  pinMode(CamIn, INPUT);
  attachInterrupt(digitalPinToInterrupt(CamIn), camera_ready, RISING);

  pinMode(CamOut, OUTPUT);
  digitalWrite(CamOut, LOW);
  
}

void z_move_complete()  {stage_ready_flag = true;}
void camera_ready()     {cam_ready_flag   = true;}

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
  if (word == "zstack") {
    scanning  = false;
    //initially set scanner to 0
    set_galvo(0);
    delay(20);
    //set up for z-stack
    nZ        = values[0];
    exposure  = values[1];
    imaging   = true;

  } else if (word == "hello") {
    Serial.print("Dual Illumination Lightsheet, firmware v: ");Serial.println(firmware);
  
  } else if (word == "scan") {
    z-stacking  = false;
    exposure  = values[0];
    scanning  = true
  } else {
    Serial.println("Unknown command");
  }
}


void z_slice(uint32_t exposure){ //do a single slice within a z-stack

  //calculate galvo step time
  float s_t = exposure/1000.0;//s_t: 10-bit DAC, spread over 1000/1024 of the DAC range

  uint32_t prev_micros = 0;
  int s= 1; //n DAC steps to move each time
// step times <2µs can't be written to the DAC fast enough, need to increase step time and decrease DAC resolution
  if(s_t < 2.0 and s_t >=1.0)     {s_t = s_t * 2.0; s=2;  }
  if(s_t < 1.0)                   {s_t = s_t * 4.0; s=4;  }
  uint32_t s_t_int = int(s_t);

  
  digitalWriteFast(CamOut, HIGH); // start camera exposure
  camera_ready_flag = false;
  delayMicroseconds(87);          // delay specified by camera datasheet
  
  
  for(int i=0;i<1024;i=i+s){
    while(micros() < prev_micros + s_t_int){} //delay for step time
    prev_micros = micros();
    set_galvo(i);
  }
  digitalWriteFast(CamOut,LOW);
  
  if(z_stacking){
    //start stage movement
    digitalWriteFast(Zo,HIGH);
    delayMicroseconds(100);
    digitalWriteFast(Zo,LOW);
    stage_ready_flag = false;
  }
  set_galvo(0);                     // return galvo to zero position ready for next scan
}


void check_serial(){
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


void loop() {
  check_serial();
  if(imaging && stage_ready_flag && cam_ready_flag){    //enter when stage and camera flags are set
     
    z_slice(exposure);                                  // take a slice
    slice_counter++;
    if(slice_counter == nZ){                            // check if stack complete
      imaging = false; slice_counter = 0;               // stop z-stacking
    }
  }

  if(scanning && cam_ready_flag){                       // start next scan when camera finished readout
    z_slice(exposure);
  }

}



void set_galvo(uint16_t value){
  value = (value & 0x3ff) << 2;
  SPI.beginTransaction(SPISettings(14000000, MSBFIRST, SPI_MODE0));
  digitalWriteFast(CS, LOW);
  SPI.transfer16(value);
  digitalWriteFast(CS, HIGH);
  SPI.endTransaction();
}