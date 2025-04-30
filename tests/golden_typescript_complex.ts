// More complex TypeScript examples for symbol extraction

import { type NextPage } from "next";

export const PI = 3.14159;

// Interface definition
export interface UserProfile {
    userId: string;
    displayName: string;
    email?: string; // Optional property
    logActivity: (action: string) => void; // Function type property
}

// Enum definition
export enum Status {
    Pending = 'PENDING',
    Active = 'ACTIVE',
    Inactive = 'INACTIVE',
}

// Namespace
namespace Utilities {
    export function log(message: string): void {
        console.log(`[UTIL]: ${message}`);
    }
    
    export class StringHelper {
        static capitalize(s: string): string {
            return s.charAt(0).toUpperCase() + s.slice(1);
        }
    }
}

// Generic Function
function identity<T>(arg: T): T {
    return arg;
}

// Generic Class
class GenericRepo<T> {
    private items: T[] = [];

    add(item: T): void {
        this.items.push(item);
    }

    getAll(): T[] {
        return this.items;
    }
}

// Arrow function assigned to a const
export const addNumbers = (a: number, b: number): number => {
    return a + b;
};

// Decorated class (conceptual - requires decorator implementation)
// function logged(constructor: Function) {
//     console.log(`Class ${constructor.name} created`);
// }

// @logged
class DecoratedClass {
    constructor(public name: string) {}

    greet() {
        return `Hello, ${this.name}`;
    }
}

// Exported function
export function calculateArea(width: number, height: number): number {
    return width * height;
}

// Async function
async function fetchData(url: string): Promise<any> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// Simple class again for baseline
class SimpleLogger {
    log(message: string) {
        console.log(message);
    }
}
