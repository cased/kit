;; Ruby symbol queries

;; Classes
(class
  name: (constant) @name) @definition.class

;; Modules
(module
  name: (constant) @name) @definition.module

;; Instance methods
(method
  name: (identifier) @name) @definition.method

;; Singleton methods (def self.foo)
(singleton_method
  name: (identifier) @name) @definition.method
