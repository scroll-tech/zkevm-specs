# JUMP op code
## Procedure
   JUMP is a an op code regarding flow control of evm. it takes the value at the top of the stack to use as the destination, which means change program counter to the destination.  That destination address should be marked 'JUMPDEST'.

   For example,  blow op code sequences, when executing to program counter '0006', the top of stack value is '0b' or 11 in decimals, Jump will change executing step to '0011' which is a valid destination as it is JUMPDEST position, if not, jump will fail as invalid jump error.

```
      0000      PUSH1 0x01 
      0002      PUSH1 0x02
      0004      PUSH1 0x0b 
      0006      JUMP 
      ...       ...   
      0011      JUMPDEST  
      0012      STOP  
      ...       ...
```

## Constraints
Let's denote 'x' for destination to jump
   1. opId = OpcodeId(0x56)
   2. state transition:  
      - gc + 1 (1 READ)
      - stack_pointer + 1 
      - pc = x
      - gas + 8  
   3. lookups:    
       - x must be top stack value
       - x must be in valid range [0, len(c.Code)] 
       - x position must be JUMPDEST

## Exceptions
   1. gas out:   remaining gas is not enough
   2. stack underflow:  when stack is empty
   3. Invalid jump (AKA ErrInvalidJump):  
   if the destination address is not JUMPDEST or x is invalid
 
## Code  
   none