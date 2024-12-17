// scanning and z-stacking working apart from stage feedback



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
volatile bool camera_ready_flag = true;     // flag denotes when camera has returned a 'readout complete' signal
const float firmware            = 2.0;      // firmware version

uint16_t slice_counter          = 0;        // for tracking slices through a z-stack
uint16_t nZ                     = 0;        // for storing total number of slices in a z-stack

bool z_stacking                 = false;    // flag denotes when z-stack is taking place
bool scanning                   = false;    // flag denotes when continuous scanning is taking place

uint16_t park                   = 0;        // galvo position to park the beam when not imaging
uint32_t exposure               = 0;        // keep track of camera exposure
uint8_t cam_delay               = 0;        // trigger scanner this time after trigger camera
const byte HALF_CLOCK_PERIOD    = 1;        // 2 uS of clock period 

uint16_t g_steps_per_FOV        = 886;      // number of steps on the galvo that corresponds to the full FOV of the camera
uint16_t g_enter_step           = 66;       // galvo step at which beam enters the camera FOV
uint16_t g_exit_step            = 952;      // galvo step at which beam leaves the camera FOV

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

  pinMode(trigger_LED, OUTPUT);
  digitalWrite(trigger_LED, LOW);
  
  set_galvo(park);
}

void z_move_complete()  {stage_ready_flag    = true; digitalWriteFast(trigger_LED, LOW);}
void camera_ready()     {camera_ready_flag   = true;}

void parseCommand(String command) {
  Serial.print("incoming command --> ");Serial.println(command);
  command.trim();
  // Ensure the command starts with a forward slash
  if (command[0] != '/') {
    Serial.println("Invalid command format... ");
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
  if (word == "stack") {
    Serial.println("entering z-stack mode");
    scanning  = false;
    //initially set scanner to 0
    set_galvo(0);
    delay(20);
    //set up for z-stack
    exposure    = values[0];
    nZ          = values[1];
    z_stacking  = true;
    Serial.print("entering z-stack mode, nZ: ");
    Serial.print(nZ);
    Serial.print("; exp: ");
    Serial.println(exposure);

  } else if (word == "hello") {
    Serial.print("Dual Illumination Lightsheet, firmware v: ");Serial.println(firmware);
  
  } else if (word == "scan") {
    Serial.println("entering scan mode");
    exposure  = values[0];
    z_stacking  = false;
    scanning  = true;
  
  } else if (word == "delay") {
    Serial.println("setting cam trigger delay");
    cam_delay   = values[0];
  
  } else if (word == "stop") {
    Serial.println("stopping");
    z_stacking  = false;
    scanning    = false;
    set_galvo(park);

  } else if (word == "galvo") {
    Serial.print("galvo to ");Serial.println(values[0]);
    z_stacking  = false;
    scanning    = false;
    set_galvo(values[0]);

  } else {
    Serial.println("Unknown command");
  }
}


void z_slice(uint32_t exposure){ //do a single slice within a z-stack, exposure in ms

  //calculate galvo step time
  float s_t = (exposure * 1000.0) / g_steps_per_FOV; //s_t: (us) exposure time spread over the numberof galvo steps in the camera  FOV 

  uint32_t prev_micros = 0;
  
  int s= 1; //n DAC steps to move each time
// step times <2µs can't be written to the DAC fast enough, need to increase step time and decrease DAC resolution
  if(s_t < 2.0 and s_t >=1.0)     {s_t = s_t * 2.0; s=2;  }
  if(s_t < 1.0)                   {s_t = s_t * 4.0; s=4;  }
  uint32_t s_t_int = int(s_t);

//need to trigger camera 87 microseconds before g_start_step
  float g_steps_for_cam = (87 / s_t) + 1; //how many galvo steps in 87us? (plus one to ensure rounding up)
  int exposure_start = g_enter_step - int(g_steps_for_cam);

  
  digitalWriteFast(CamOut,LOW);
  //SCAN
  for(int g=0;g<1024;g=g+s){
    if(g==exposure_start)     {digitalWriteFast(CamOut, HIGH); camera_ready_flag = false; }  // trigger camera ~ 87 us before beam enters FOV
    
    while(micros() < prev_micros + s_t_int){} //delay for step time
    prev_micros = micros();
    set_galvo(g);
    
    if(g==g_exit_step)        {digitalWriteFast(CamOut, LOW);}                              // end camera trigger pulse
    
  }
  
  

  if(z_stacking){
    //start stage movement
    digitalWriteFast(Zo,HIGH);
    delayMicroseconds(100);
    digitalWriteFast(Zo,LOW);
    stage_ready_flag = false; digitalWriteFast(trigger_LED, HIGH);
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
  if(z_stacking  && camera_ready_flag){    //enter when stage and camera flags are set
     //&& stage_ready_flag
    z_slice(exposure);                                  // take a slice
    slice_counter++;
    Serial.print("z:");Serial.println(slice_counter);
    if(slice_counter == nZ){                            // check if stack complete
      z_stacking = false;                               // stop z-stacking
      slice_counter = 0;                                // reset slice counter
      set_galvo(park);
    }
  }

  if(scanning && camera_ready_flag){                    // start next scan when camera finished readout
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