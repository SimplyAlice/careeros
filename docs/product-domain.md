# Product Domain

The new domain will eventually centre around:

User
  |
  +-- Context
  |
  +-- Preferences
  |
  +-- Plans
          |
          +-- Plan Items
          |
          +-- Constraints
          |
          +-- Decisions
          |
          +-- Budget
          |
          +-- Sources

Potential information entities:

- Place
- Restaurant
- Activity
- Event
- Transport Option
- Accommodation
- Product
- Service Provider

These should not all be implemented immediately.

The first domain slice should prove that the system can:

1. accept an intention
2. capture relevant constraints
3. produce structured options
4. assemble a plan
5. explain the plan
6. allow the user to modify it
7. persist the resulting plan

External data providers will be introduced behind interfaces so that the domain is
not tightly coupled to one provider.