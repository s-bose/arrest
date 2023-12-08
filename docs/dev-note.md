## Regarding Path Parameter idiosyncrasies
If you decide to specify your path parameters using kwargs, only two options are there.
- Using kwargs as path parameters
- Embedding path parameters as f-strings

The second option is less error-prone as the full URL path is being constructed, while the first option is preferable if you don't like working with f-strings.
It is an experimental feature which I thought would be beneficial but only time will tell how useful it really is.
