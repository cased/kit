// Golden test file for C# symbol extraction
using System;
using System.Collections.Generic;

namespace GoldenTest.Models
{
    public interface IEntity
    {
        int Id { get; }
    }

    public class User : IEntity
    {
        public int Id { get; set; }
        public string Name { get; set; }

        public User() {}

        public User(int id, string name)
        {
            Id = id;
            Name = name;
        }

        public void UpdateName(string newName)
        {
            Name = newName;
        }
    }

    public struct Point
    {
        public int X { get; }
        public int Y { get; }

        public Point(int x, int y)
        {
            X = x;
            Y = y;
        }
    }

    public record Person(string FirstName, string LastName);

    public enum Status
    {
        Active,
        Inactive
    }

    public delegate void StatusChanged(Status newStatus);
}
