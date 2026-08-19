---
name: typescript-typing-expert
description: TypeScript and modern frontend typing standards for this repo (packages/app-backstage/) — focusing on strict typing, TSDoc, React component props, and avoid any. Use when writing or reviewing TypeScript code in this repo.
---

# TypeScript Typing & Frontend Expert

## Toolchain & Standards
*   **Target:** TypeScript 5.x + Strict Mode enabled (`tsconfig.json`).
*   **Lint / Format:** Integrated via project toolchain (`ruff`/`eslint` equivalent depending on Backstage workspace).

## 1. Modern Type & Interface Principles
*   **Interfaces over Types for Objects:** Use `interface` for extensible object shapes (especially React props and API models); use `type` for unions, primitives, and mapped/utility types (e.g., `type Status = 'idle' | 'loading'`).
*   **Avoid `any` strictly:** Never use `any`. Use `unknown` if the type is truly uncertain, followed by type narrowing (guards/assertions). For third-party libraries missing types, declare modules cleanly in `.d.ts` files instead of falling back to `any`.
*   **Readonly by default:** Use `readonly` modifiers for data structures, props, and state properties that should not mutate (e.g., `readonly items: readonly string[]`).

## 2. React & Backstage Component Typing
*   **Props Typing:** Always define explicit component props using `interface`. Avoid inline object types.
*   **Functional Components:** Type components directly with standard function syntax and explicit return types or standard React functional component conventions:
    ```typescript
    interface UserCardProps {
      readonly userId: string;
      readonly name: string;
    }

    export const UserCard = ({ userId, name }: UserCardProps): JSX.Element => {
      return <div>{name} ({userId})</div>;
    };
    ```
*   **Event Handling & Hooks:** Use accurate generic types for hooks (e.g., `useState<User | null>(null)`) and event handlers (e.g., `React.ChangeEvent<HTMLInputElement>`).

## 3. Utility Types & Advanced Narrowing
*   **Built-in Utilities:** Leverage standard utility types (`Partial`, `Required`, `Pick`, `Omit`, `Record`) instead of duplicating structural definitions.
*   **Discriminated Unions:** Use literal type discriminants for complex state management or component variants:
    ```typescript
    type NetworkState = 
      | { readonly status: 'loading' }
      | { readonly status: 'success'; readonly data: UserData }
      | { readonly status: 'error'; readonly error: Error };
    ```
*   **Type Guards:** Write custom type guard functions (`isUser(val: unknown): val is User`) instead of casting with `as User`.

## 4. Documentation & TSDoc Standards
*   **Mandatory TSDoc:** Use `/** ... */` for all exported components, interfaces, utility functions, and hooks.
*   **Concise Explanations:** Keep inline comments brief (maximum 1 sentence) to prevent clutter.
*   **No Type Duplication:** Do not restate types in comments if TypeScript already enforces them.