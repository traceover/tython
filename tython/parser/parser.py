############################################
# PARSER
############################################

from tython.tokens import TokenType
from tython.errors import SyntaxError
from .result import ParseResult
from .nodes import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.advance()

    def advance(self):
        """
        Increments index and returns token at that position
        """
        self.tok_idx += 1
        if self.tok_idx < len(self.tokens):
            self.current_tok = self.tokens[self.tok_idx]
        return self.current_tok

    def parse(self):
        res = self.expr()
        if not res.error and self.current_tok.type != TokenType.EOF:
            print(self.tokens)
            return res.failure(
                SyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '+', '-', '*', '/', or '^'",
                )
            )
        return res

    ############################################

    def atom(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TokenType.INT, TokenType.FLOAT, TokenType.NUMBER):
            res.register_advancement()
            self.advance()
            if tok.type == TokenType.INT:
                return res.success(IntNode(tok))
            elif tok.type == TokenType.FLOAT:
                return res.success(FloatNode(tok))
            return res.success(NumberNode(tok))

        elif tok.type == TokenType.IDENTIFIER:
            res.register_advancement()
            self.advance()
            return res.success(VarAccessNode(tok))

        elif tok.type == TokenType.LPAREN:
            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error:
                return res
            if self.current_tok.type == TokenType.RPAREN:
                res.register_advancement()
                self.advance()
                return res.success(expr)
            else:
                return res.failure(
                    SyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ')'",
                    )
                )

        return res.failure(
            SyntaxError(
                tok.pos_start,
                tok.pos_end,
                "Expected int, float, identifier, '+', '-' or '('",
            )
        )

    def power(self):
        return self.bin_op(self.atom, (TokenType.POWER,), self.factor)

    def factor(self):
        """
        Looks for int, float, or number, returns ParseResult(NumberNode)
        """
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TokenType.PLUS, TokenType.MINUS):
            res.register_advancement()
            self.advance()
            factor = res.register(self.factor())
            if res.error:
                return res
            return res.success(UnaryOpNode(tok, factor))

        return self.power()

    def term(self):
        """
        Looks for mul or div, repeats until no more are found, returns BinOpNode
        """
        return self.bin_op(self.factor, (TokenType.MUL, TokenType.DIV))

    def arith_expr(self):
        return self.bin_op(self.term, (TokenType.PLUS, TokenType.MINUS))

    def comp_expr(self):
        res = ParseResult()

        if self.current_tok.matches(TokenType.KEYWORD, "not"):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()

            node = res.register(self.comp_expr())
            if res.error:
                return res
            return res.success(UnaryOpNode(op_tok, node))

        node = res.register(
            self.bin_op(
                self.arith_expr,
                (
                    TokenType.EE,
                    TokenType.NE,
                    TokenType.LT,
                    TokenType.GT,
                    TokenType.LTE,
                    TokenType.GTE,
                ),
            )
        )

        if res.error:
            return res.failure(
                SyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected int, float, identifier, '+', '-','(', 'not",
                )
            )

        return res.success(node)

    def expr(self):
        """
        Looks for plus or minus, repeats until no more are found, returns BinOpNode
        """
        res = ParseResult()

        if self.current_tok.type == TokenType.TYPE:
            type = self.current_tok
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TokenType.IDENTIFIER:
                return res.failure(
                    SyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier",
                    )
                )

            var_name = self.current_tok
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TokenType.EQ:
                return res.failure(
                    SyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected '='",
                    )
                )

            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error:
                return res
            return res.success(VarAssignNode(var_name, expr, type))

        node = res.register(
            self.bin_op(
                self.comp_expr, ((TokenType.KEYWORD, "and"), (TokenType.KEYWORD, "or"))
            )
        )

        if res.error:
            return res.failure(
                SyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected declaration, int, float, identifier, '+', '-' or '('",
                )
            )

        return res.success(node)

    ############################################

    def bin_op(self, func, ops, func_b=None):
        if func_b == None:
            func_b = func

        res = ParseResult()
        left = res.register(func())
        if res.error:
            return res

        while (
            self.current_tok.type in ops
            or (self.current_tok.type, self.current_tok.value) in ops
        ):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()
            right = res.register(func())
            if res.error:
                return res
            left = BinOpNode(left, op_tok, right)

        return res.success(left)  # ParseResult(BinOpNode)