import { useContext, createContext } from "react";

export const ReadOnlyContext = createContext(false);

export const useReadOnly = () => useContext(ReadOnlyContext);
