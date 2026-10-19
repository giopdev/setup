## General
 - If I ask a question it doesn't always mean I want you to implement something, instead I might be trying to discuss something

## Coding Standards
- In general try to follow YAGNI (You Are Not Gonna Need It) to avoid over abstracting
- Comments should stand on their own and code should be self-documenting (i.e. long descriptive variable names) and comments that don't refer back to prompts or conversations

## Documentation Standards
 - Prefer One-liners for installing dependencies and building when possible
 - Prefer to document Usage patterns and give example commands
 - Documentation should link to and cite relevent source (e.g., some piece of documentation that discusses a niche case for some specific linux syscall should cite the relevant manpage or kernel documentation that supports it)
 - Prefer more depth in documentation (e.g., don't handwave large swathes of detail by assuming the reader knows)
 - Prefer to include high-level system design figures when explaining logic
 - All acronyms should always be written as such unless they are commonly known (e.g., GRUB, UEFI, and GNU are examples that don't need definition) - TIAA (This is an acronym)
 - Like comments, documentation should stand on its own and not refer back to prompts
 ### Hypothetical for example
*Note that this documentation isn't a full documentation example*

#### User Prompt
```
Make me a crud image app called "MyImg" that isn't like imgur (e.g., don't have voting)
```

#### Bad Documetation Generation
```
# MyImg

MyImg is a crud image app that is not like imgur
MyImg does not have voting and allows users to view and upload images
...
```

#### Reasonable Documetation Generation
```
# MyImg

MyImg is an image app that allows users to view and upload images
...
```

### Another hypothetical for example
*Note that this documentation isn't a full documentation example*

#### Bad Documentation
```
SystemName implements x feature with y, not z
```

#### Reasonable Documentation
```
SystemName implements x feature with y
```

## Building, Running, and Testing
 - While testing is good, there is no need for endless useless smoke tests every time a minor change is made.
