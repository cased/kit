package main

import "fmt"

// User represents a user in the system.
type User struct {
	ID   int
	Name string
}

// Greeter defines an interface for greeting.
type Greeter interface {
	Greet() string
}

// Greet implements the Greeter interface for User.
func (u User) Greet() string {
	return fmt.Sprintf("Hello, my name is %s", u.Name)
}

// Add calculates the sum of two integers.
func Add(a, b int) int {
	return a + b
}

// Standalone function
func HelperFunction() {
	fmt.Println("This is a helper function.")
}

func main() {
	user := User{ID: 1, Name: "Alice"}
	fmt.Println(user.Greet())
	fmt.Println(Add(5, 3))
	HelperFunction()
}
