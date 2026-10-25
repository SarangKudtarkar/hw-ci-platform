// Exhaustive self-checking testbench for the 4-bit adder.
// Like many testbenches it always calls $finish, so the simulator exits 0
// even when a check fails; the CI relies on the printed markers.
`timescale 1ns/1ps

module adder_tb;
    reg  [3:0] a, b;
    reg        cin;
    wire [3:0] sum;
    wire       cout;

    integer i, j, k;
    integer errors;
    reg [4:0] expected;

    adder dut (.a(a), .b(b), .cin(cin), .sum(sum), .cout(cout));

    initial begin
        errors = 0;

        for (i = 0; i < 16; i = i + 1)
            for (j = 0; j < 16; j = j + 1)
                for (k = 0; k < 2; k = k + 1) begin
                    a = i[3:0];
                    b = j[3:0];
                    cin = k[0];
                    #1;
                    expected = a + b + cin;
                    if ({cout, sum} !== expected) begin
                        errors = errors + 1;
                        $display("ERROR: %0d + %0d + %0d = %0d, got %0d",
                                 a, b, cin, expected, {cout, sum});
                    end
                end

        if (errors == 0)
            $display("TEST PASSED: 512 combinations checked");
        else
            $display("TEST FAILED: %0d mismatching combinations", errors);

        $finish;
    end
endmodule
