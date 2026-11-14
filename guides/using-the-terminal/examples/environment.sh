# A program gets a copy of its parent's environment, and ends with an exit status.
# Each child here is a second bash, run the way a shell runs any command.

export GREETING=hello
echo "the child sees GREETING = $(bash -c 'echo "$GREETING"')"

echo "the child changed its copy to $(bash -c 'GREETING=changed; echo "$GREETING"')"
echo "the parent still has GREETING = $GREETING"

echo "a variable nobody set: $(bash -c 'echo "${NOT_SET_ANYWHERE:-(not set)}"')"

output=$(bash -c 'echo "all good"')
echo "success: exit status $? | output: $output"

# The same failing child twice: once for its standard output, once for its standard error.
failing='echo $((10 / 0))'
output=$(bash -c "$failing" 2> /dev/null)
echo "failure: exit status $? | output: '$output'"
error=$(bash -c "$failing" 2>&1 > /dev/null)
echo "the error went to standard error; it ends with:"
echo "  ${error##*: }"
