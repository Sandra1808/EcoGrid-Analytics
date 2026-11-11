package EcoGrid.Backend.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;

@Entity
@Table(name = "ALERTAS_OPERATIVAS")
public class AlertasOperativa {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDALERTA", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDTIEMPO", nullable = false)
    private Tiempohorario idtiempo;

    @Size(max = 50)
    @NotNull
    @Column(name = "NIVELALERTA", nullable = false, length = 50)
    private String nivelalerta;

    @Column(name = "COSTEPOTENCIALEUR", precision = 14, scale = 4)
    private BigDecimal costepotencialeur;

    @Lob
    @Column(name = "MENSAJE")
    private String mensaje;

    @Size(max = 50)
    @NotNull
    @Column(name = "ESTADO", nullable = false, length = 50)
    private String estado;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDUSUARIORESPONSABLE")
    private Usuario idusuarioresponsable;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Tiempohorario getIdtiempo() {
        return idtiempo;
    }

    public void setIdtiempo(Tiempohorario idtiempo) {
        this.idtiempo = idtiempo;
    }

    public String getNivelalerta() {
        return nivelalerta;
    }

    public void setNivelalerta(String nivelalerta) {
        this.nivelalerta = nivelalerta;
    }

    public BigDecimal getCostepotencialeur() {
        return costepotencialeur;
    }

    public void setCostepotencialeur(BigDecimal costepotencialeur) {
        this.costepotencialeur = costepotencialeur;
    }

    public String getMensaje() {
        return mensaje;
    }

    public void setMensaje(String mensaje) {
        this.mensaje = mensaje;
    }

    public String getEstado() {
        return estado;
    }

    public void setEstado(String estado) {
        this.estado = estado;
    }

    public Usuario getIdusuarioresponsable() {
        return idusuarioresponsable;
    }

    public void setIdusuarioresponsable(Usuario idusuarioresponsable) {
        this.idusuarioresponsable = idusuarioresponsable;
    }

}