// scanning and z-stacking working?



#include <Arduino.h>
const String firmware            = "2.2 (M)";      // firmware version


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
const byte CamOut               = 40;
const byte CamIn                = 22;
const byte trigger_LED          = 23;
const byte trigger_Filter       = 16;
const byte trigger_Laser        = 35;

//LED power
uint16_t LED_power = 20;  //0-50 is useable range


volatile bool stage_ready_flag  = true;     // flag denoting when stage moves are complete
volatile bool camera_ready_flag = true;     // flag denotes when camera has returned a 'readout complete' signal


uint16_t slice_counter          = 0;        // for tracking slices through a z-stack
uint16_t nZ                     = 0;        // for storing total number of slices in a z-stack

bool z_stacking                 = false;    // flag denotes when z-stack is taking place
bool scanning                   = false;    // flag denotes when continuous scanning is taking place
bool musical                    = false;    // keeps track of if in musical imaging mode (no z trigger)

uint16_t park                   = 0;        // galvo position to park the beam when not imaging
uint32_t exposure               = 0;        // keep track of camera exposure
uint8_t cam_delay               = 0;        // trigger scanner this time after trigger camera
const byte HALF_CLOCK_PERIOD    = 1;        // 2 uS of clock period 


uint16_t g_enter_step           = 53;       // galvo step at which beam enters the camera FOV
uint16_t g_exit_step            = 931;      // galvo step at which beam leaves the camera FOV
uint16_t g_steps_per_FOV        = (g_exit_step - g_enter_step); // number of steps on the galvo that corresponds to the full FOV of the camera

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

  attachInterrupt(digitalPinToInterrupt(Zi), z_move_complete, RISING);
  
  pinMode(CamIn, INPUT);
  attachInterrupt(digitalPinToInterrupt(CamIn), camera_ready, RISING);

  pinMode(CamOut, OUTPUT);
  digitalWrite(CamOut, LOW);

  pinMode(trigger_Filter, OUTPUT);
  digitalWrite(trigger_Filter, LOW);

  pinMode(trigger_LED, OUTPUT);
  digitalWrite(trigger_LED, HIGH);
  
  set_galvo(park);

  analogWriteResolution(8);
}

void z_move_complete()  {stage_ready_flag    = true; digitalWriteFast(trigger_Filter, LOW);}
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
    scanning = false;
    z_stacking  = true;
    
    //initially set scanner to 0
    set_galvo(park);
    delay(20);
    //set up for z-stack
    exposure    = values[0];
    nZ          = values[1];
    Serial.print("entering z-stack mode, nZ: ");
    Serial.print(nZ);
    Serial.print("; exp: ");
    Serial.println(exposure);
  
  } else if (word == "musical") {
    Serial.print("Setting Musical Mode: ");
    if(values[0]==1){musical = true; Serial.println("True");}
    if(values[0]==0){musical = false; Serial.println("False");}
  
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
    digitalWrite(trigger_LED,1);

  } else if (word == "galvo") {
    Serial.print("galvo to ");Serial.println(values[0]);
    z_stacking  = false;
    scanning    = false;
    set_galvo(values[0]);

  } else if (word == "led") {
    Serial.print("LED: ");Serial.println(values[0]);
    if(values[0] == 0){analogWrite(trigger_LED,255);}
    else if(values[0] == 1){analogWrite(trigger_LED,50 - LED_power);}
    else{Serial.println("invalid value for command 'led', use 0 or 1");}

  } else {
    Serial.println("Unknown command");
  }
}


void z_slice(uint32_t exposure){ //do a single slice within a z-stack, exposure in ms

  //calculate galvo step time
  float s_t = (exposure * 1000.0) / g_steps_per_FOV; //s_t: (us) exposure time spread over the number of galvo steps in the camera FOV 

  uint32_t prev_micros = 0;
  

// step times <2µs can't be written to the DAC fast enough, need to increase step time and decrease DAC resolution

  uint32_t s_t_int = int(s_t);

//need to trigger camera 9 * line interval microseconds before g_start_step
  float line_interval = (exposure / 2048); //line interval = exposure/no. of pixel lines
  float cam_delay_steps = ((9 * line_interval) / s_t) + 1; //how many galvo steps before g_enter_step (plus one to ensure rounding up)
  int cam_trigger_step = g_enter_step - int(cam_delay_steps);
  
  digitalWriteFast(CamOut,LOW);
  //SCAN
  for(int g=0;g<1024;g++){
    if(g==cam_trigger_step)     {digitalWriteFast(CamOut, HIGH); camera_ready_flag = false; }  // trigger camera ~ 87 us before beam enters FOV
    
    while(micros() < prev_micros + s_t_int){} //delay for step time
    prev_micros = micros();
    set_galvo(g);

  }
  digitalWriteFast(CamOut, LOW);

  if(z_stacking && musical == false){
    //start stage movement
    digitalWriteFast(Zo,HIGH);
    delayMicroseconds(1);
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
  if(musical){stage_ready_flag=true;}
  if(z_stacking  && camera_ready_flag  &&  stage_ready_flag){    //enter when stage and camera flags are set
    
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