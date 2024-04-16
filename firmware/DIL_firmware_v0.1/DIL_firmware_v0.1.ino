#include <SPI.h>

//galvos
const byte CS    = 12; 
const byte CLOCK = 13;
const byte DATA  = 11;
//stage
const byte Xo  = 31;
const byte Yo  = 29;
const byte Zo  = 27;
const byte Xi  = 32;
const byte Yi  = 30;
const byte Zi  = 28;
volatile bool x_stage_flag = false; //flags for tracking when stage moves are complete
volatile bool y_stage_flag = false;
volatile bool z_stage_flag = false;
//digital I/O
const byte CamOut  = 23;
const byte CamIn   = 22;
const byte trigger_LED     = 16;
const byte trigger_Filter  = 40;
const byte trigger_Laser   = 35;
const byte IOf  = 33;


bool verbose = false;


const byte HALF_CLOCK_PERIOD = 1; //2 uS of clock period 

void setup() {
  Serial.begin(115200);
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
  attachInterrupt(digitalPinToInterrupt(Xi), x_move_complete, FALLING);
  attachInterrupt(digitalPinToInterrupt(Yi), y_move_complete, FALLING);
  attachInterrupt(digitalPinToInterrupt(Zi), z_move_complete, FALLING);
  
}

void x_move_complete(){x_stage_flag = true;}
void y_move_complete(){y_stage_flag = true;}
void z_move_complete(){z_stage_flag = true;}

uint32_t prev_scan = 0; // previous scan time
uint32_t Scan = 0;      // store exposure time (µs), 0 for no scan


void loop() {
checkSerial();
if(Scan > 0){
  if(micros() > prev_scan + Scan){
    sweep(Scan);
    }
  }
}

//~~~~~~~~~~~~~~~~~~~~~~~~~~ Serial communications ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
String device = "";
String command1 = "";
String command2 = "";
String command3 = "";
String command4 = "";
String command5 = "";

int serial_part = 0;
bool Verbose = true;

void checkSerial(){
  char rc;
  while (Serial.available()) {
   rc = Serial.read();
   if (rc == 47)      {serial_part = 1; device = "";command1 = "";command2 = "";}  // '/' char
   else if (rc == 46)      {serial_part += 1;}                                     // '.' char
   else if (rc == 59)      {respond(device,command1,command2,command3,command4,command5); serial_part = 0;}   // ';' char
   else if (serial_part == 1){device   += rc;}
   else if (serial_part == 2){command1 += rc;}
   else if (serial_part == 3){command2 += rc;}
   else if (serial_part == 4){command3 += rc;}
   else if (serial_part == 5){command4 += rc;}
   else if (serial_part == 6){command5 += rc;}
 }
}

void hablar(String parabla){
  if(Verbose == true){Serial.println(parabla);}
}

void respond(String device,String command1, String command2, String command3, String command4, String command5) {
//z-stack
    if(device == "Stack")               {z_stack(command1.toInt(),command2.toInt(),command3.toInt());}
//test functions    
    if(device == "G")                   {set_galvo(command1.toInt());}  // Galvo command
    if(device == "X")                   {increment_stage(0);}           // Stage command
    if(device == "Y")                   {increment_stage(1);}           // Stage command
    if(device == "Z")                   {increment_stage(2);}           // Stage command
    if(device == "S")                   {sweep(command1.toInt());}      // Sweep galvos - transit time in milliseconds
    if(device == "Scan")                {Scan = command1.toInt()*1000;}       // Repeatedly sweep galvos - 0 to turn off (ms)
    
//handshake    
    if(device == "hello")               {Serial.println("Dual Illumination Lightsheet");}
}



           //number of z, z step size, exposure time
void z_stack(uint16_t nZ, uint32_t sZ, uint32_t E){
  for(int z=0;z<nZ;z++){
    //trigger laser
    digitalWrite(trigger_Laser,1);
    //trigger galvo sweep and camera
    sweep(E);
    //laser off
    digitalWrite(trigger_Laser,0);
  //move Z
    increment_stage(2);
  //confirm move
    while(z_stage_flag==false){}
  }
  //respond to PC
}

void sweep(uint32_t exposure){ //input exposure time in microSeconds
  //calculate step time
  float s_t = exposure/1000.0;//s_t: 10-bit DAC, spread over 1000/1024 of the DAC range

  uint32_t prev_micros = 0;
  int s= 1; //n DAC steps to move each time
// step times <2µs can't be written to the DAC fast enough, need to increase step time and decrease DAC resolution
  if(s_t < 2.0 and s_t >=1.0)     {s_t = s_t * 2.0; s=2;  }
  if(s_t < 1.0)                   {s_t = s_t * 4.0; s=4;  }
  uint32_t s_t_int = int(s_t);
  

  bool exp_complete = false;
  bool exp_start    = false;
  
  for(int i=0;i<1024;i=i+s){
    while(micros() < prev_micros + s_t_int){} //delay for step time
    prev_micros = micros();
    set_galvo(i);
    if(i>=12   and exp_start==false)   {digitalWriteFast(CamOut,HIGH);} //trigger camera at 12th unit
    if(i>=1012 and exp_complete==false){digitalWriteFast(CamOut,LOW); } //camera end after 1000 units
  }
}

void increment_stage(int axis){
  if(axis==2){
    z_stage_flag = false;
    digitalWrite(Zo,0);
    delayMicroseconds(1);
    digitalWrite(Zo,1);
  }
  if(axis==1){
    y_stage_flag = false;
    digitalWrite(Yo,0);
    delayMicroseconds(1);
    digitalWrite(Yo,1);
  }
  if(axis==0){
    x_stage_flag = false;
    digitalWrite(Xo,0);
    delayMicroseconds(1);
    digitalWrite(Xo,1);
  }
}

void set_galvo(uint16_t value){
  //value = value + 512; //offset to that 0 is centre value
  SPI.beginTransaction(SPISettings(14000000, MSBFIRST, SPI_MODE0));
  digitalWriteFast(CS, LOW);
  SPI.transfer(highByte(value << 2));
  SPI.transfer(lowByte(value));
  digitalWriteFast(CS, HIGH);
  SPI.endTransaction();
}
