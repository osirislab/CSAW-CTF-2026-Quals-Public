const frames = [
    String.raw`
                 

    (. .)
   o__|__oo
      | 
     / \
    /   \
    `,

    String.raw`
                 

    (. .)
   o__|__oo
      | 
     / \
    /   \
    `,

    String.raw`
                 

    (. .)
   o__|__oo
      | 
     / \
    /   \
    `,

    String.raw`
                 

    (. .)
   o__|_
      | \oo
     / \
    /   \
    `,

    String.raw`
                 

    (. .)
   o__|_
      o/o  
     / \
    /   \
    `,

    String.raw`
                 
 
    (. .)
   o__0_
      | \o
     / \
    /   \
    `,

    String.raw`
                 
       
    (0 .)
   o__|_
      | \o
     / \
    /   \
    `,

    String.raw`
                 
    o 
    (. .)
   o__|_
      | \o
     / \
    /   \
    `,

    String.raw`
                 
    o 
    (. .)
     _|_
   o/ | \o
     / \
    /   \
    `,

    String.raw`
                 
        
   0(. .)
     _|_
     \o \o
     / \
    /   \
    `,

    String.raw`
                 
        
    (. .)
  0  _0_
    / | \o
     / \
    /   \
    `,

    String.raw`
                 
        
    (. 0)
     _|_
   o/ | \o
     / \
    /   \
    `,

    String.raw`
                 
        o
    (. .)
     _|_
   o/ | \o 
     / \
    /   \
    `,

    String.raw`
                 
        o
    (. .)
     _|_
   o/ o/ 
     / \
    /   \
    `,

    //15
    String.raw`
                 
        
    (. .)0
     _0_
   o/ | \
     / \
    /   \
    `,

    String.raw`
                 
        
    (0 .)
     _|_ 0
   o/ | \
     / \
    /   \
    `,

    String.raw`
                 
    o   
    (. .)
     _|_ 
   o/ | \o
     / \
    /   \
    `,

    String.raw`
                 
    o   
    (. .)
     _|_ 
     \o \o
     / \
    /   \
    `,

    String.raw`
                 
       
   0(. .)
     _0_ 
    / | \o
     / \
    /   \
    `,

    String.raw`
                 
       
    (. 0)
   0 _|_ 
    / | \o
     / \
    /   \
    `,

    String.raw`
                 
        o
    (. .)
     _|_ 
   o/ | \o
     / \
    /   \
    `,

    String.raw`
                 
        o
    (. .)
     _|_ 
   o/ o/
     / \
    /   \
    `,

    //23 End of loop
    String.raw`
                 
        
    (. .)0
     _0_ 
   o/ |/
     / \
    /   \
    `,
]


// Start infinite loop from frame 15
const firstLoopFrame = 15;
const finalLoopFrame = 22; //23, but array index starts at 0
let currentFrame = 0;
let loopCount = 0;

let animateAscii = () => {
    document.querySelector('#ascii-display').textContent = frames[currentFrame]
    // currentFrame = (currentFrame + 1) % frames.length;
    currentFrame++;
    if (currentFrame >= frames.length)
        currentFrame = firstLoopFrame;
}

setInterval(animateAscii, 140);